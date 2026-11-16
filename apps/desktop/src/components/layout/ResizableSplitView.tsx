/**
 * ResizableSplitView Component
 * Governed by 529 Engineering Standards:
 * - Kiosk Ergonomics: Expanded hit target (>= 48px interactive drag area)
 * - Persistent split ratio across app restarts via usePaneResize
 * - Smooth dragging via pointer capture & ARIA separator accessibility
 */

import { type FC, type ReactNode } from 'react';
import { usePaneResize, type UsePaneResizeOptions } from '../../hooks/usePaneResize';
import { GripVertical } from 'lucide-react';

export interface ResizableSplitViewProps extends UsePaneResizeOptions {
  leftPane: ReactNode;
  rightPane: ReactNode;
  className?: string;
  leftPaneClassName?: string;
  rightPaneClassName?: string;
}

export const ResizableSplitView: FC<ResizableSplitViewProps> = ({
  leftPane,
  rightPane,
  className = '',
  leftPaneClassName = '',
  rightPaneClassName = '',
  initialRatio = 0.5,
  minLeftWidth = 350,
  minRightWidth = 350,
  storageKey = 'finsight:split-view:ratio',
  dividerWidth = 6,
}) => {
  const {
    splitRatio,
    isDragging,
    containerRef,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handleKeyDown,
    resetRatio,
    leftPaneStyle,
    rightPaneStyle,
  } = usePaneResize({
    initialRatio,
    minLeftWidth,
    minRightWidth,
    storageKey,
    dividerWidth,
  });

  return (
    <div
      ref={containerRef}
      className={`relative flex h-full w-full overflow-hidden ${
        isDragging ? 'select-none cursor-col-resize' : ''
      } ${className}`}
    >
      {/* LEFT PANE */}
      <div
        style={leftPaneStyle}
        className={`h-full overflow-hidden ${leftPaneClassName}`}
        data-testid="resizable-left-pane"
      >
        {leftPane}
      </div>

      {/* DRAGGABLE RESIZE DIVIDER */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Khung điều chỉnh độ rộng màn hình"
        aria-valuenow={Math.round(splitRatio * 100)}
        aria-valuemin={10}
        aria-valuemax={90}
        tabIndex={0}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onKeyDown={handleKeyDown}
        onDoubleClick={resetRatio}
        title="Kéo để thay đổi tỷ lệ khung nhìn (Nhấp đúp để đặt lại 50/50)"
        style={{ width: `${dividerWidth}px` }}
        className={`relative z-30 h-full flex items-center justify-center cursor-col-resize transition-colors duration-150 outline-none focus:ring-2 focus:ring-indigo-400 ${
          isDragging
            ? 'bg-indigo-500 shadow-[0_0_12px_rgba(99,102,241,0.7)]'
            : 'bg-slate-800 hover:bg-indigo-500/80'
        }`}
        data-testid="resizable-divider"
      >
        {/* Expanded 48px hit area for kiosk / touch target accessibility */}
        <div
          aria-hidden="true"
          className="absolute inset-y-0 -left-5 -right-5 z-40 cursor-col-resize"
        />

        {/* Visual Grip Handle Indicator */}
        <div
          aria-hidden="true"
          className={`pointer-events-none z-50 flex items-center justify-center w-4 h-8 rounded-full border transition-all duration-150 ${
            isDragging
              ? 'bg-indigo-600 border-indigo-300 text-white shadow-md'
              : 'bg-slate-900 border-slate-700 text-slate-400 group-hover:text-white'
          }`}
        >
          <GripVertical className="w-3 h-3" />
        </div>
      </div>

      {/* RIGHT PANE */}
      <div
        style={rightPaneStyle}
        className={`h-full overflow-hidden ${rightPaneClassName}`}
        data-testid="resizable-right-pane"
      >
        {rightPane}
      </div>
    </div>
  );
};
