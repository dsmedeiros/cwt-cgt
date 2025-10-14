import path from 'node:path';

import { describe, expect, it } from 'vitest';

import { cmdBaseline, type BaselineCommandOptions } from '../baselines';
import { cwtSimRoot, repoRoot } from '../paths';

describe('cmdBaseline', () => {
  const pythonExe = '/usr/bin/python';
  const shared: Pick<BaselineCommandOptions, 'axisMap' | 'outputDir' | 'steps' | 'seed'> = {
    axisMap: 'configs/axis.yml',
    outputDir: 'artifacts/baselines/runA',
    steps: 250,
    seed: 17,
  };

  const sharedArgs = [
    '--axis-map',
    path.resolve(shared.axisMap as string),
    '--output-dir',
    path.resolve(shared.outputDir as string),
    '--steps',
    String(shared.steps),
    '--seed',
    String(shared.seed),
  ];

  it.each([
    ['ising', ['--axes', 'T', 'h']],
    ['kuramoto', ['--graph-kind', 'ring3', '--graph-param', 'n=64']],
    ['percolation', ['--graph', 'grid', '--save-summary']],
    ['sis', ['--infection-rate', '0.4']],
  ] as Array<[BaselineCommandOptions['model'], string[]]>) (
    'builds module strategy invocation for %s baseline',
    (model, extraArgs) => {
      const plan = cmdBaseline(pythonExe, {
        strategy: 'module',
        model,
        args: extraArgs,
        ...shared,
      });

      expect(plan.command).toBe(pythonExe);
      expect(plan.cwd).toBe(repoRoot);
      expect(plan.pythonPath).toBeTruthy();
      expect(plan.pythonPath ?? '').toContain(repoRoot);
      expect(plan.pythonPath ?? '').toContain(cwtSimRoot);
      expect(plan.args.slice(0, 2)).toEqual(['-m', `baselines.${model}.run`]);
      expect(plan.args.slice(2)).toEqual([...sharedArgs, ...extraArgs]);
      expect(plan.cli).toContain(`cd ${repoRoot}`);
    },
  );

  it.each([
    ['ising'],
    ['kuramoto'],
    ['percolation'],
    ['sis'],
  ] as Array<[BaselineCommandOptions['model']]>) (
    'builds py_path strategy invocation for %s baseline',
    (model) => {
      const plan = cmdBaseline('python3', {
        strategy: 'py_path',
        model,
        ...shared,
        args: ['--flag', 'value'],
      });

      expect(plan.command).toBe('python3');
      expect(plan.cwd).toBe(repoRoot);
      expect(plan.args[0]).toBe(path.join(repoRoot, 'cwt-sim', 'baselines', model, 'run.py'));
      expect(plan.args.slice(1)).toEqual([...sharedArgs, '--flag', 'value']);
      expect(plan.pythonPath).toBeTruthy();
      expect(plan.pythonPath ?? '').toContain(cwtSimRoot);
      expect(plan.pythonPath ?? '').toContain(repoRoot);
      expect(plan.cli).toContain(`cd ${repoRoot}`);
    },
  );

  it('throws when python executable is missing', () => {
    expect(() =>
      cmdBaseline('', { strategy: 'module', model: 'ising', args: [] }),
    ).toThrowError('pythonExe is required');
  });

  it('omits optional arguments when they are empty', () => {
    const plan = cmdBaseline(pythonExe, {
      strategy: 'module',
      model: 'ising',
      axisMap: null,
      outputDir: '',
      steps: undefined,
      seed: '',
      args: [null, '--flag', undefined, 'value'] as unknown as Array<string | number>,
    });

    expect(plan.args).toEqual(['-m', 'baselines.ising.run', '--flag', 'value']);
  });

  it('throws when steps or seed are not integers', () => {
    expect(() =>
      cmdBaseline('python', {
        strategy: 'module',
        model: 'ising',
        steps: 2.5,
      }),
    ).toThrowError('steps must be an integer.');

    expect(() =>
      cmdBaseline('python', {
        strategy: 'module',
        model: 'ising',
        seed: 'abc',
      }),
    ).toThrowError('seed must be numeric.');
  });

  it('throws when the model is unsupported', () => {
    expect(() =>
      cmdBaseline('python', {
        strategy: 'module',
        model: 'unknown' as BaselineCommandOptions['model'],
      }),
    ).toThrowError('Unsupported baseline model: unknown');
  });
});
