import { useEffect, useId, useRef, useState } from 'react';

import type React from 'react';
import type { Phase1HeatmapKind, Phase1TopologySummary } from '../utils/artifacts';
import { PHASE1_TOPOLOGY_FIELDS } from '../utils/artifacts';

type Point = { x: number; y: number };

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.25;

const DOM_DELTA_LINE = 1;
const DOM_DELTA_PAGE = 2;
const ESTIMATED_LINE_HEIGHT = 16;

const normalizeWheelDelta = (delta: number, mode: number) => {
  if (mode === DOM_DELTA_LINE) {
    return delta * ESTIMATED_LINE_HEIGHT;
  }
  if (mode === DOM_DELTA_PAGE) {
    return delta * (typeof window !== 'undefined' ? window.innerHeight : 800);
  }
  return delta;
};

const focusableSelector =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const formatTopologyValue = (value: number | null) =>
  value == null ? '–' : Number.isInteger(value) ? value.toFixed(0) : value.toFixed(3);

export type HeatmapImage = {
  substrate: string;
  graph: string;
  kind: Phase1HeatmapKind;
  relativePath: string;
  dataUrl: string;
  label: string;
  topology: Phase1TopologySummary | null;
};

type Phase1HeatmapViewerProps = {
  heatmap: HeatmapImage;
  onClose: () => void;
};

const clampZoom = (value: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number(value.toFixed(2))));

const Phase1HeatmapViewer = ({ heatmap, onClose }: Phase1HeatmapViewerProps) => {
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const pointerRef = useRef<{
    active: boolean;
    pointerId: number | null;
    lastPosition: Point;
  }>({
    active: false,
    pointerId: null,
    lastPosition: { x: 0, y: 0 },
  });
  const headingId = useId();
  const statsHeadingId = useId();

  useEffect(() => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
    setIsPanning(false);
  }, [heatmap]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  useEffect(() => {
    const modalNode = modalRef.current;
    if (!modalNode) {
      return;
    }

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const resolveFocusables = () =>
      Array.from(modalNode.querySelectorAll<HTMLElement>(focusableSelector)).filter(
        (element) => !element.hasAttribute('data-focus-guard') && !element.hasAttribute('disabled'),
      );
    const getFocusablePair = () => {
      const elements = resolveFocusables();
      if (elements.length === 0) {
        return { elements, first: modalNode, last: modalNode };
      }
      return { elements, first: elements[0], last: elements[elements.length - 1] };
    };
    const { first: initialFocusTarget } = getFocusablePair();
    initialFocusTarget.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab') {
        return;
      }
      const { elements, first, last } = getFocusablePair();
      if (elements.length === 0) {
        event.preventDefault();
        modalNode.focus();
        return;
      }
      const activeElement = document.activeElement as HTMLElement | null;
      if (event.shiftKey) {
        if (activeElement === first || !modalNode.contains(activeElement)) {
          event.preventDefault();
          last.focus();
        }
        return;
      }
      if (activeElement === last || !modalNode.contains(activeElement)) {
        event.preventDefault();
        first.focus();
      }
    };

    const handleDocumentFocus = (event: FocusEvent) => {
      if (modalNode.contains(event.target as Node)) {
        return;
      }
      const { first } = getFocusablePair();
      first.focus();
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('focus', handleDocumentFocus, true);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('focus', handleDocumentFocus, true);
      if (previouslyFocused) {
        previouslyFocused.focus();
      }
    };
  }, [onClose]);

  useEffect(() => {
    if (zoom === 1) {
      setOffset({ x: 0, y: 0 });
      setIsPanning(false);
    }
  }, [zoom]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (!pointerRef.current.active || pointerRef.current.pointerId !== event.pointerId) {
        return;
      }
      event.preventDefault();
      const deltaX = event.clientX - pointerRef.current.lastPosition.x;
      const deltaY = event.clientY - pointerRef.current.lastPosition.y;
      pointerRef.current.lastPosition = { x: event.clientX, y: event.clientY };
      setOffset((current) => ({ x: current.x + deltaX, y: current.y + deltaY }));
    };

    const stopPointerTracking = (event: PointerEvent) => {
      if (pointerRef.current.pointerId != null && event.currentTarget instanceof HTMLElement) {
        try {
          event.currentTarget.releasePointerCapture(pointerRef.current.pointerId);
        } catch {
          // Ignore release failures when the pointer is no longer captured.
        }
      }
      pointerRef.current = {
        active: false,
        pointerId: null,
        lastPosition: { x: 0, y: 0 },
      };
      setIsPanning(false);
    };

    canvas.addEventListener('pointermove', handlePointerMove);
    canvas.addEventListener('pointerup', stopPointerTracking);
    canvas.addEventListener('pointercancel', stopPointerTracking);
    canvas.addEventListener('pointerleave', stopPointerTracking);

    return () => {
      canvas.removeEventListener('pointermove', handlePointerMove);
      canvas.removeEventListener('pointerup', stopPointerTracking);
      canvas.removeEventListener('pointercancel', stopPointerTracking);
      canvas.removeEventListener('pointerleave', stopPointerTracking);
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const normalizedDeltaY = normalizeWheelDelta(event.deltaY, event.deltaMode);
      if (normalizedDeltaY === 0) {
        return;
      }

      const rect = canvas.getBoundingClientRect();
      const focalPointX = event.clientX - rect.left - rect.width / 2;
      const focalPointY = event.clientY - rect.top - rect.height / 2;

      setZoom((currentZoom) => {
        const zoomDelta = -Math.sign(normalizedDeltaY) * ZOOM_STEP;
        if (zoomDelta === 0) {
          return currentZoom;
        }
        const nextZoom = clampZoom(currentZoom + zoomDelta);
        if (nextZoom === currentZoom) {
          return currentZoom;
        }
        if (nextZoom === MIN_ZOOM) {
          setOffset({ x: 0, y: 0 });
        } else {
          setOffset((currentOffset) => {
            const scaleRatio = nextZoom / currentZoom;
            return {
              x: focalPointX - (focalPointX - currentOffset.x) * scaleRatio,
              y: focalPointY - (focalPointY - currentOffset.y) * scaleRatio,
            };
          });
        }
        return nextZoom;
      });
    };

    canvas.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      canvas.removeEventListener('wheel', handleWheel);
    };
  }, []);

  const handlePointerDown: React.PointerEventHandler<HTMLDivElement> = (event) => {
    const pointerType = event.pointerType as string;
    const isMousePointer = pointerType === 'mouse' || pointerType === '' || pointerType === 'pen';
    const isRightClick = event.button === 2;
    if ((isMousePointer && !isRightClick) || zoom === 1) {
      return;
    }
    event.preventDefault();
    pointerRef.current = {
      active: true,
      pointerId: event.pointerId,
      lastPosition: { x: event.clientX, y: event.clientY },
    };
    setIsPanning(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handleOverlayMouseDown: React.MouseEventHandler<HTMLDivElement> = (event) => {
    if (event.target === event.currentTarget) {
      event.preventDefault();
      onClose();
    }
  };

  const handleZoomIn = () => setZoom((value) => clampZoom(value + ZOOM_STEP));
  const handleZoomOut = () => setZoom((value) => clampZoom(value - ZOOM_STEP));
  const handleZoomChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextZoom = clampZoom(Number(event.target.value));
    setZoom(nextZoom);
  };
  const handleResetView = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
    setIsPanning(false);
  };

  const transform = `translate3d(${offset.x}px, ${offset.y}px, 0) scale(${zoom})`;
  const canvasCursor = zoom > 1 && isPanning ? 'grabbing' : 'default';

  return (
    <div className="phase1__heatmap-viewer" role="presentation" onMouseDown={handleOverlayMouseDown}>
      <div
        className="phase1__heatmap-viewer-modal"
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        tabIndex={-1}
      >
        <div className="phase1__heatmap-viewer-header">
          <h4 id={headingId}>{heatmap.label}</h4>
          <button type="button" className="phase1__heatmap-viewer-close" onClick={onClose} aria-label="Close heatmap viewer">
            ×
          </button>
        </div>
        {heatmap.topology ? (
          <section className="phase1__heatmap-viewer-stats" aria-labelledby={statsHeadingId}>
            <h5 id={statsHeadingId}>Topology descriptors</h5>
            <dl>
              {PHASE1_TOPOLOGY_FIELDS.map(({ key, label }) => (
                <div key={key} className="phase1__heatmap-viewer-row">
                  <dt>{label}</dt>
                  <dd>{formatTopologyValue(heatmap.topology?.[key] ?? null)}</dd>
                </div>
              ))}
            </dl>
          </section>
        ) : null}
        <div className="phase1__heatmap-viewer-controls">
          <button type="button" onClick={handleZoomOut} aria-label="Zoom out" disabled={zoom <= MIN_ZOOM}>
            −
          </button>
          <input
            type="range"
            min={MIN_ZOOM}
            max={MAX_ZOOM}
            step={ZOOM_STEP}
            value={zoom}
            onChange={handleZoomChange}
            aria-label="Zoom level"
            className="phase1__heatmap-viewer-slider"
          />
          <button type="button" onClick={handleZoomIn} aria-label="Zoom in" disabled={zoom >= MAX_ZOOM}>
            +
          </button>
          <button type="button" onClick={handleResetView} aria-label="Reset view" className="phase1__heatmap-viewer-reset">
            Reset
          </button>
        </div>
        <div
          className="phase1__heatmap-viewer-canvas"
          ref={canvasRef}
          onPointerDown={handlePointerDown}
          onContextMenu={(event) => event.preventDefault()}
          role="presentation"
          style={{ cursor: canvasCursor }}
        >
          <img
            src={heatmap.dataUrl}
            alt={heatmap.label}
            className="phase1__heatmap-viewer-image"
            style={{ transform }}
            draggable={false}
          />
        </div>
      </div>
    </div>
  );
};

export default Phase1HeatmapViewer;
