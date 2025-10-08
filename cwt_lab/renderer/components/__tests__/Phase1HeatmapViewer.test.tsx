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
});
