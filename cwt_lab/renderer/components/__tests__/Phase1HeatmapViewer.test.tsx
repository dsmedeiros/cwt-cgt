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
};

describe('Phase1HeatmapViewer', () => {
  it('renders the viewer and closes via interactions and keyboard', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    expect(screen.getByRole('heading', { name: sampleHeatmap.label })).toBeInTheDocument();

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

  it('pans the heatmap when scrolling without modifiers', () => {
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    const canvas = document.querySelector('.phase1__heatmap-viewer-canvas');
    const image = document.querySelector<HTMLImageElement>('.phase1__heatmap-viewer-image');
    const slider = screen.getByRole('slider', { name: /zoom level/i });

    if (!(canvas instanceof HTMLElement) || !image) {
      throw new Error('Heatmap canvas could not be found');
    }

    fireEvent.change(slider, { target: { value: '2' } });

    fireEvent.wheel(canvas, { deltaX: 30, deltaY: -10 });

    expect(image.style.transform).toContain('translate3d(-30px, 10px, 0)');
    expect(image.style.transform).toContain('scale(2)');
  });

  it('zooms the heatmap around the cursor when the user scrolls with a modifier key', () => {
    const onClose = vi.fn();

    render(<Phase1HeatmapViewer heatmap={sampleHeatmap} onClose={onClose} />);

    const canvas = document.querySelector('.phase1__heatmap-viewer-canvas');
    const image = document.querySelector<HTMLImageElement>('.phase1__heatmap-viewer-image');

    if (!(canvas instanceof HTMLElement) || !image) {
      throw new Error('Heatmap canvas could not be found');
    }

    const rectSpy = vi.spyOn(canvas, 'getBoundingClientRect');
    rectSpy.mockReturnValue(new DOMRect(0, 0, 400, 300));

    fireEvent.wheel(canvas, { ctrlKey: true, deltaY: -40, clientX: 200, clientY: 150 });

    expect(image.style.transform).toContain('scale(1.25)');

    rectSpy.mockRestore();
  });
});
