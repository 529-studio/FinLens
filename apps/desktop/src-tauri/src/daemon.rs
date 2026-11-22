use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use serde::{Deserialize, Serialize};

pub const DEFAULT_DAEMON_PORT: u16 = 8765;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonStatus {
    pub is_running: bool,
    pub port: u16,
    pub managed_child: bool,
    pub pid: Option<u32>,
    pub message: String,
}

pub struct DaemonManager {
    child: Mutex<Option<Child>>,
    port: u16,
}

impl DaemonManager {
    pub fn new(port: u16) -> Self {
        Self {
            child: Mutex::new(None),
            port,
        }
    }

    /// Check if daemon responds to HTTP GET /health on 127.0.0.1:port
    pub fn is_healthy(&self) -> bool {
        let addr = SocketAddr::from(([127, 0, 0, 1], self.port));
        let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(600)) else {
            return false;
        };

        let _ = stream.set_read_timeout(Some(Duration::from_millis(800)));
        let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));

        let request = format!(
            "GET /health HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\n\r\n",
            self.port
        );
        if stream.write_all(request.as_bytes()).is_err() {
            return false;
        }

        let mut buffer = [0u8; 512];
        let Ok(n) = stream.read(&mut buffer) else {
            return false;
        };

        let response = String::from_utf8_lossy(&buffer[..n]);
        response.contains("200 OK") || response.contains("healthy")
    }

    /// Get current status info
    pub fn get_status(&self) -> DaemonStatus {
        let guard = self.child.lock().unwrap();
        let healthy = self.is_healthy();
        let (managed, pid) = match guard.as_ref() {
            Some(c) => (true, Some(c.id())),
            None => (false, None),
        };

        DaemonStatus {
            is_running: healthy,
            port: self.port,
            managed_child: managed,
            pid,
            message: if healthy {
                format!("Core engine daemon is online at 127.0.0.1:{}", self.port)
            } else {
                format!("Core engine daemon is offline on port {}", self.port)
            },
        }
    }

    /// Locate virtualenv python and main.py, and start daemon if not already healthy
    pub fn ensure_started(&self, repo_root: &Path) -> Result<DaemonStatus, String> {
        if self.is_healthy() {
            return Ok(self.get_status());
        }

        let python_candidates = [
            repo_root.join("packages/core-engine/.venv/bin/python"),
            repo_root.join(".venv/bin/python"),
            PathBuf::from("python3"),
        ];

        let python_path = python_candidates
            .into_iter()
            .find(|p| p.exists() || p.to_str() == Some("python3"))
            .ok_or_else(|| "Could not find Python binary in virtualenv".to_string())?;

        let script_path = repo_root.join("packages/core-engine/src/main.py");
        if !script_path.exists() {
            return Err(format!("Daemon entrypoint not found at: {:?}", script_path));
        }

        let mut cmd = Command::new(&python_path);
        cmd.arg(&script_path)
            .current_dir(repo_root)
            .env("PYTHONPATH", repo_root.join("packages/core-engine/src"))
            .env("FINTRACE_DAEMON_PORT", self.port.to_string())
            .env("FINTRACE_DAEMON_HOST", "127.0.0.1")
            .env("FINSIGHT_DAEMON_PORT", self.port.to_string())
            .env("FINSIGHT_DAEMON_HOST", "127.0.0.1")
            .stdout(Stdio::null())
            .stderr(Stdio::null());

        let child = cmd
            .spawn()
            .map_err(|e| format!("Failed to spawn daemon process: {}", e))?;

        {
            let mut guard = self.child.lock().unwrap();
            *guard = Some(child);
        }

        // Poll for readiness up to 10 seconds (20 iterations * 500ms)
        for _ in 0..20 {
            std::thread::sleep(Duration::from_millis(500));
            if self.is_healthy() {
                return Ok(self.get_status());
            }
        }

        Err("Daemon spawned but failed health check within 10s".to_string())
    }

    /// Terminate managed child daemon cleanly and wait to prevent zombie processes
    pub fn terminate(&self) {
        let mut guard = self.child.lock().unwrap();
        if let Some(mut child) = guard.take() {
            let pid = child.id();
            eprintln!("[DaemonManager] Terminating child daemon (PID {})...", pid);
            let _ = child.kill();
            let _ = child.wait();
            eprintln!("[DaemonManager] Child daemon terminated cleanly (0 zombie processes).");
        }
    }
}

impl Drop for DaemonManager {
    fn drop(&mut self) {
        self.terminate();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_daemon_status_serialization() {
        let status = DaemonStatus {
            is_running: true,
            port: 8765,
            managed_child: false,
            pid: None,
            message: "Running".to_string(),
        };
        let json = serde_json::to_string(&status).unwrap();
        assert!(json.contains("8765"));
        assert!(json.contains("is_running\":true"));
    }

    #[test]
    fn test_daemon_offline_check() {
        // Port 59999 is highly unlikely to have a server listening
        let manager = DaemonManager::new(59999);
        assert!(!manager.is_healthy());
        let status = manager.get_status();
        assert!(!status.is_running);
        assert_eq!(status.port, 59999);
    }

    #[test]
    fn test_daemon_terminate_zero_zombies() {
        let manager = DaemonManager::new(59998);
        // Spawn a lightweight sleep process
        let child = Command::new("python3")
            .arg("-c")
            .arg("import time; time.sleep(30)")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("Failed to spawn test child process");

        let pid = child.id();
        {
            let mut guard = manager.child.lock().unwrap();
            *guard = Some(child);
        }

        let status_before = manager.get_status();
        assert!(status_before.managed_child);
        assert_eq!(status_before.pid, Some(pid));

        // Terminate process
        manager.terminate();

        let status_after = manager.get_status();
        assert!(!status_after.managed_child);
        assert_eq!(status_after.pid, None);

        // Verify with kill -0 that process is not running (exits with non-zero when PID does not exist)
        #[cfg(unix)]
        {
            let output = Command::new("kill")
                .arg("-0")
                .arg(pid.to_string())
                .output()
                .expect("Failed to execute kill -0 check");
            assert!(
                !output.status.success(),
                "Process PID {} must not be running after termination",
                pid
            );
        }
    }
}
