import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import Phase1HeatmapViewer, { type HeatmapImage } from '../Phase1HeatmapViewer';

const sampleHeatmap: HeatmapImage = {
  substrate: 'substrate_a',
  graph: 'graph_a',
  kind: 'omega_heatmap',
  relativePath: 'runs/run-1/heatmap.png',
  dataUrl: 'data:image/png;base64,xyz',
  label: 'Substrate A – Heatmap',
  topology: null,
};

if (typeof PointerEvent === 'undefined') {
  class PointerEventPolyfill extends MouseEvent {
    pointerId: number;
    pointerType?: string;

    constructor(type: string, eventInitDict: PointerEventInit = {}) {
      super(type, eventInitDict);
      this.pointerId = eventInitDict.pointerId ?? 0;
      this.pointerType = eventInitDict.pointerType;
    }
  }

  // @ts-expect-error - polyfilling PointerEvent for the test environment.
  globalThis.PointerEvent = PointerEventPolyfill;
}

describe('Phase1HeatmapViewer', () => {
  it('renders the viewer and closes via interactions and keyboard', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    expect(screen.getByRole('heading', { name: sampleHeatmap.label })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /topology descriptors/i })).not.toBeInTheDocument();

    const closeButton = screen.getByRole('button', { name: /close heatmap viewer/i });
    await user.click(closeButton);
    expect(onClose).toHaveBeenCalledTimes(1);

    const overlay = document.querySelector('.phase1__heatmap-viewer');
    if (!(overlay instanceof HTMLElement)) {
      throw new Error('Viewer overlay not found');
    }
    fireEvent.mouseDown(overlay);
    expect(onClose).toHaveBeenCalledTimes(2);

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it('traps focus within the viewer controls', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    const closeButton = screen.getByRole('button', { name: /close heatmap viewer/i });
    const zoomSlider = screen.getByRole('slider', { name: /zoom level/i });
    const zoomIn = screen.getByRole('button', { name: /zoom in/i });
    const reset = screen.getByRole('button', { name: /reset view/i });

    expect(closeButton).toHaveFocus();

    await user.tab();
    expect(zoomSlider).toHaveFocus();

    await user.tab();
    expect(zoomIn).toHaveFocus();

    await user.tab();
    expect(reset).toHaveFocus();

    await user.tab();
    expect(closeButton).toHaveFocus();

    await user.tab({ shift: true });
    expect(reset).toHaveFocus();
  });

  it('displays topology descriptors when provided', () => {
    const onClose = vi.fn();
    const heatmapWithTopology: HeatmapImage = {
      ...sampleHeatmap,
      topology: {
        clustering: 0.123,
        pathLength: 2.5,
        degreeVariance: 0.75,
        assortativity: -0.12,
      },
    };

    render(<Phase1HeatmapViewer heatmap={heatmapWithTopology} onClose={onClose} />);

    expect(screen.getByRole('heading', { name: /topology descriptors/i })).toBeInTheDocument();
    expect(screen.getByText('0.123')).toBeInTheDocument();
    expect(screen.getByText('2.500')).toBeInTheDocument();
    expect(screen.getByText('0.750')).toBeInTheDocument();
    expect(screen.getByText('-0.120')).toBeInTheDocument();
  });

  it('zooms the heatmap around the cursor when the user scrolls', () => {
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    const canvas = document.querySelector('.phase1__heatmap-viewer-canvas');
    const image = document.querySelector<HTMLImageElement>('.phase1__heatmap-viewer-image');

    if (!(canvas instanceof HTMLElement) || !image) {
      throw new Error('Heatmap canvas could not be found');
    }

    const rectSpy = vi.spyOn(canvas, 'getBoundingClientRect');
    rectSpy.mockReturnValue(new DOMRect(0, 0, 400, 300));

    fireEvent.wheel(canvas, { deltaY: -40, clientX: 200, clientY: 150 });

    expect(image.style.transform).toContain('scale(1.25)');
    expect(image.style.transform).toContain('translate3d(0px, 0px, 0)');

    rectSpy.mockRestore();
  });

  it('pans the heatmap when dragging with the right mouse button while zoomed in', () => {
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    const canvas = document.querySelector('.phase1__heatmap-viewer-canvas');
    const image = document.querySelector<HTMLImageElement>('.phase1__heatmap-viewer-image');
    const slider = screen.getByRole('slider', { name: /zoom level/i });

    if (!(canvas instanceof HTMLElement) || !image) {
      throw new Error('Heatmap canvas could not be found');
    }

    canvas.setPointerCapture = vi.fn();
    canvas.releasePointerCapture = vi.fn();

    fireEvent.change(slider, { target: { value: '2' } });

    const pointerDownEvent = new PointerEvent('pointerdown', {
      pointerId: 1,
      button: 2,
      clientX: 150,
      clientY: 150,
      pointerType: 'mouse',
      bubbles: true,
    });
    const pointerMoveEvent = new PointerEvent('pointermove', {
      pointerId: 1,
      clientX: 190,
      clientY: 120,
      bubbles: true,
    });
    const pointerUpEvent = new PointerEvent('pointerup', {
      pointerId: 1,
      bubbles: true,
    });

    fireEvent(canvas, pointerDownEvent);
    fireEvent(canvas, pointerMoveEvent);
    fireEvent(canvas, pointerUpEvent);

    expect(canvas.setPointerCapture).toHaveBeenCalled();
    expect(image.style.transform).toContain('translate3d(40px, -30px, 0)');
    expect(image.style.transform).toContain('scale(2)');
  });
});
