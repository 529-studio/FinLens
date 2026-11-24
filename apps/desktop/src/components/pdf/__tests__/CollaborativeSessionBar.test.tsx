// @vitest-environment jsdom

/**
 * Component Tests for CollaborativeSessionBar
 * Validates 3 UI states, kiosk touch targets (>= 48px), Rule 15 zero raw emojis,
 * and peer presence / annotation counter rendering.
 * Governed by Sprint 11 Task S11-03, AGENTS.md Rule 1, Rule 13, Rule 15.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { CollaborativeSessionBar } from '../CollaborativeSessionBar';
import { UserPresenceDTO, AuditAnnotationDTO } from '../../../types/session_sync.types';

describe('CollaborativeSessionBar Component', () => {
  afterEach(() => {
    cleanup();
  });

  const mockPeers: UserPresenceDTO[] = [
    {
      user_id: 'alice_senior',
      name: 'Alice Senior',
      role: 'senior_auditor',
      color: '#4F46E5',
      active_page: 3,
      cursor_x: 200,
      cursor_y: 400,
      last_seen: Date.now() / 1000,
    },
    {
      user_id: 'bob_analyst',
      name: 'Bob Analyst',
      role: 'junior_analyst',
      color: '#059669',
      active_page: 5,
      cursor_x: 600,
      cursor_y: 700,
      last_seen: Date.now() / 1000,
    },
  ];

  const mockAnnotations: AuditAnnotationDTO[] = [
    {
      annotation_id: 'anno_1',
      document_id: 'VNM_2023',
      page_number: 3,
      bounding_box: [100, 200, 300, 400],
      comment: 'Cần kiểm tra thuyết minh 4',
      author_id: 'alice_senior',
      author_name: 'Alice Senior',
      created_at: Date.now() / 1000,
      resolved: false,
    },
  ];

  it('renders Skeleton Loading state when syncStatus is connecting', () => {
    render(
      <CollaborativeSessionBar
        sessionId="audit-room-101"
        documentId="VNM_2023"
        syncStatus="connecting"
        activeUsers={[]}
        annotations={[]}
      />
    );

    const skeleton = screen.getByTestId('collaborative-skeleton');
    expect(skeleton).toBeDefined();
    expect(skeleton.className).toContain('animate-pulse');
  });

  it('renders Error state with retry button when syncStatus is error', () => {
    const handleRetry = vi.fn();
    render(
      <CollaborativeSessionBar
        sessionId="audit-room-101"
        documentId="VNM_2023"
        syncStatus="error"
        errorMessage="Mất kết nối máy chủ WebSocket"
        activeUsers={[]}
        annotations={[]}
        onRetry={handleRetry}
      />
    );

    const errorContainer = screen.getByTestId('collaborative-error');
    expect(errorContainer).toBeDefined();
    expect(screen.getByText(/Lỗi đồng bộ phòng kiểm toán:/i)).toBeDefined();
    expect(screen.getByText(/Mất kết nối máy chủ WebSocket/i)).toBeDefined();

    const retryBtn = screen.getByTestId('collaborative-retry-btn');
    expect(retryBtn.className).toContain('min-h-[48px]');

    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('renders Empty state when connected but no other peers are online', () => {
    render(
      <CollaborativeSessionBar
        sessionId="audit-room-101"
        documentId="VNM_2023"
        syncStatus="connected"
        activeUsers={[
          {
            user_id: 'current_user',
            name: 'Current User',
            role: 'junior_analyst',
            color: '#4F46E5',
            active_page: 1,
            last_seen: Date.now() / 1000,
          },
        ]}
        currentUserId="current_user"
        annotations={[]}
      />
    );

    const emptyContainer = screen.getByTestId('collaborative-empty');
    expect(emptyContainer).toBeDefined();
    expect(screen.getByText('Chưa có đồng nghiệp nào tham gia phòng')).toBeDefined();
  });

  it('renders active peer badges and triggers page jump on click', () => {
    const handleJumpToPage = vi.fn();
    render(
      <CollaborativeSessionBar
        sessionId="audit-room-101"
        documentId="VNM_2023"
        syncStatus="connected"
        activeUsers={mockPeers}
        annotations={mockAnnotations}
        currentUserId="current_user"
        onJumpToPage={handleJumpToPage}
      />
    );

    expect(screen.getByTestId('collaborative-peers-list')).toBeDefined();
    expect(screen.getByText('Alice Senior')).toBeDefined();
    expect(screen.getByText('Bob Analyst')).toBeDefined();
    expect(screen.getByText('P.3')).toBeDefined();
    expect(screen.getByText('P.5')).toBeDefined();

    // Click on Alice's peer badge to jump to page 3
    const aliceBtn = screen.getByText('Alice Senior').closest('button');
    expect(aliceBtn).toBeDefined();
    if (aliceBtn) fireEvent.click(aliceBtn);
    expect(handleJumpToPage).toHaveBeenCalledWith(3);
  });

  it('enforces kiosk ergonomics (>= 48px touch targets) on all interactive buttons', () => {
    const { container } = render(
      <CollaborativeSessionBar
        sessionId="audit-room-101"
        documentId="VNM_2023"
        syncStatus="connected"
        activeUsers={mockPeers}
        annotations={mockAnnotations}
        currentUserId="current_user"
      />
    );

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      expect(btn.className).toContain('min-h-[48px]');
    });
  });

  it('strictly adheres to Rule 15: Zero raw Unicode emojis in rendered UI', () => {
    const { container } = render(
      <CollaborativeSessionBar
        sessionId="audit-room-101"
        documentId="VNM_2023"
        syncStatus="connected"
        activeUsers={mockPeers}
        annotations={mockAnnotations}
        currentUserId="current_user"
      />
    );

    const emojiRegex = /\p{Extended_Pictographic}/u;
    expect(emojiRegex.test(container.innerHTML)).toBe(false);
  });
});
