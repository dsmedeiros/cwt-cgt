import { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Data, Layout } from 'plotly.js';

import { useDemoMode, type DemoRecipe } from '../demo/DemoModeContext';

const buildRecipeLayout = (title: string): Partial<Layout> => ({
  title,
  margin: { t: 40, r: 12, b: 40, l: 48 },
  height: 300,
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  template: 'plotly_dark',
  legend: { orientation: 'h', y: -0.2 },
  font: { family: 'Inter, sans-serif' },
});

const buildRecipeData = (recipe: DemoRecipe): Data[] => [
  {
    type: 'scatter',
    mode: 'lines+markers',
    x: recipe.history.map((point) => point.iteration),
    y: recipe.history.map((point) => point.phiFlux),
    name: 'Φ flux',
    hovertemplate: 'Iter %{x}: %{y:.3f}<extra>Φ flux</extra>',
  },
  {
    type: 'scatter',
    mode: 'lines+markers',
    x: recipe.history.map((point) => point.iteration),
    y: recipe.history.map((point) => point.guard),
    name: 'Guard margin',
    hovertemplate: 'Iter %{x}: %{y:.3f}<extra>Guard</extra>',
    yaxis: 'y2',
  },
];

const buildDiffLabel = (a: number, b: number) => {
  if (!Number.isFinite(a) || !Number.isFinite(b) || b === 0) {
    return '–';
  }
  const delta = ((a - b) / Math.abs(b)) * 100;
  const formatted = Math.abs(delta) < 0.1 ? `${delta.toFixed(2)}%` : `${delta.toFixed(1)}%`;
  return delta > 0 ? `+${formatted}` : formatted;
};

const RecipeComparison = () => {
  const { enabled, recipes } = useDemoMode();
  const [leftId, setLeftId] = useState<string | null>(null);
  const [rightId, setRightId] = useState<string | null>(null);

  useEffect(() => {
    if (!recipes.length) {
      setLeftId(null);
      setRightId(null);
      return;
    }
    setLeftId((prev) => (prev && recipes.some((recipe) => recipe.record.id === prev) ? prev : recipes[0]?.record.id ?? null));
    setRightId((prev) =>
      prev && recipes.some((recipe) => recipe.record.id === prev)
        ? prev
        : recipes[1]?.record.id ?? recipes[0]?.record.id ?? null,
    );
  }, [recipes]);

  const leftRecipe = useMemo(
    () => recipes.find((recipe) => recipe.record.id === leftId) ?? null,
    [recipes, leftId],
  );
  const rightRecipe = useMemo(
    () => recipes.find((recipe) => recipe.record.id === rightId) ?? null,
    [recipes, rightId],
  );

  const sharedMetrics = useMemo(() => {
    if (!leftRecipe || !rightRecipe) {
      return [];
    }
    const leftMap = new Map(leftRecipe.metrics.map((entry) => [entry.label, entry]));
    const result: Array<{ label: string; left: number; right: number; unit?: string }> = [];
    rightRecipe.metrics.forEach((metric) => {
      const leftMetric = leftMap.get(metric.label);
      if (!leftMetric) {
        return;
      }
      result.push({ label: metric.label, left: leftMetric.value, right: metric.value, unit: metric.unit });
    });
    return result;
  }, [leftRecipe, rightRecipe]);

  const distinctOptions = useMemo(() => recipes.map((recipe) => ({ id: recipe.record.id, name: recipe.record.name })), [
    recipes,
  ]);

  return (
    <div className="panel recipe-comparison">
      <header className="recipe-comparison__header">
        <div>
          <h2>Recipe comparison</h2>
          <p>
            Select two saved protocols to compare their guard compliance, Φ flux, and convergence behaviour. Demo mode
            seeds the list with curated examples.
          </p>
        </div>
        <div className="recipe-comparison__selectors">
          <label>
            <span>Recipe A</span>
            <select value={leftId ?? ''} onChange={(event) => setLeftId(event.target.value)}>
              {distinctOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Recipe B</span>
            <select value={rightId ?? ''} onChange={(event) => setRightId(event.target.value)}>
              {distinctOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {!enabled ? (
        <p className="recipe-comparison__placeholder">
          Enable demo mode to populate the comparison table with pre-baked recipes, or connect to a live backend to list
          your own protocols.
        </p>
      ) : recipes.length < 2 ? (
        <p className="recipe-comparison__placeholder">Add more saved recipes to enable side-by-side comparison.</p>
      ) : !leftRecipe || !rightRecipe ? (
        <p className="recipe-comparison__placeholder">Select two recipes to view their metrics.</p>
      ) : (
        <div className="recipe-comparison__content">
          <section className="recipe-comparison__metrics" aria-label="Metric comparison">
            <table>
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col">Recipe A</th>
                  <th scope="col">Recipe B</th>
                  <th scope="col">Δ (A vs B)</th>
                </tr>
              </thead>
              <tbody>
                {sharedMetrics.map((metric) => (
                  <tr key={metric.label}>
                    <th scope="row">{metric.label}</th>
                    <td>{metric.unit ? `${metric.left.toFixed(3)} ${metric.unit}` : metric.left.toFixed(3)}</td>
                    <td>{metric.unit ? `${metric.right.toFixed(3)} ${metric.unit}` : metric.right.toFixed(3)}</td>
                    <td>{buildDiffLabel(metric.left, metric.right)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="recipe-comparison__plots" aria-label="Evolution plots">
            <div>
              <Plot
                data={buildRecipeData(leftRecipe)}
                layout={{
                  ...buildRecipeLayout(leftRecipe.record.name),
                  yaxis: { title: 'Φ flux' },
                  yaxis2: { overlaying: 'y', side: 'right', title: 'Guard margin' },
                }}
                useResizeHandler
                className="recipe-comparison__plot"
                style={{ width: '100%', height: '100%' }}
                config={{ displayModeBar: false }}
              />
            </div>
            <div>
              <Plot
                data={buildRecipeData(rightRecipe)}
                layout={{
                  ...buildRecipeLayout(rightRecipe.record.name),
                  yaxis: { title: 'Φ flux' },
                  yaxis2: { overlaying: 'y', side: 'right', title: 'Guard margin' },
                }}
                useResizeHandler
                className="recipe-comparison__plot"
                style={{ width: '100%', height: '100%' }}
                config={{ displayModeBar: false }}
              />
            </div>
          </section>
        </div>
      )}
    </div>
  );
};

export default RecipeComparison;
