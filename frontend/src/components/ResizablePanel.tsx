import React, { useState, useEffect, useRef } from 'react';

interface ResizablePanelProps {
  children: React.ReactNode;
  initialWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  initialHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  side: 'left' | 'right' | 'bottom';
  className?: string;
}

export function ResizablePanel({ children, initialWidth = 400, minWidth = 300, maxWidth = 800, initialHeight = 300, minHeight = 150, maxHeight = 600, side, className = '' }: ResizablePanelProps) {
  const isVertical = side === 'bottom';
  const [size, setSize] = useState(isVertical ? initialHeight : initialWidth);
  const isResizing = useRef(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      
      document.body.classList.add('select-none');

      if (side === 'right') {
        const newWidth = document.body.clientWidth - e.clientX;
        setSize(Math.max(minWidth, Math.min(maxWidth, newWidth)));
      } else if (side === 'bottom') {
        const newHeight = document.body.clientHeight - e.clientY;
        setSize(Math.max(minHeight, Math.min(maxHeight, newHeight)));
      }
    };
    
    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.classList.remove('select-none');
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.classList.remove('select-none');
    };
  }, [side, minWidth, maxWidth]);

  const handleMouseDown = () => {
    isResizing.current = true;
  };

  return (
    <div style={{ [isVertical ? 'height' : 'width']: size }} className={`relative flex-shrink-0 flex flex-col ${className}`}>
      {side === 'right' && (
        <div 
          onMouseDown={handleMouseDown} 
          className="w-2 hover:w-3 hover:bg-indigo-500/50 absolute left-0 top-0 bottom-0 cursor-col-resize z-[100] transition-colors -translate-x-1/2"
        />
      )}
      {side === 'bottom' && (
        <div 
          onMouseDown={handleMouseDown} 
          className="h-2 hover:h-3 hover:bg-indigo-500/50 absolute top-0 left-0 right-0 cursor-row-resize z-[100] transition-colors -translate-y-1/2"
        />
      )}
      <div className="flex-1 w-full h-full min-h-0 min-w-0 flex flex-col">
        {children}
      </div>
    </div>
  );
}
