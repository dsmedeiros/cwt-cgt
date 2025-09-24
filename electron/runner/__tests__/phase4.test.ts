import path from 'path';

import { cmdTorusPlateau, cmdWilson3D } from '../phase4';

describe('cmdWilson3D', () => {
  it('builds a module invocation with arbitrary axes', () => {
    const spec = cmdWilson3D('python', {
      axes3: ['alpha', 'beta', 'gamma'],
      center: [0.1, -0.2, 0.3],
      amplitudes: [0.4, 0.2, 0.1],
      steps: 48,
      handleSteps: 24,
      settle: 80,
      fsGuard: 0.18,
      graph: 'ring3',
      seed: 11,
      etaQ: 0.5,
      zeta: 0.2,
      omegaScale: 1.25,
      outDir: '/tmp/out',
    });

    expect(spec.command).toBe('python');
    expect(spec.args.slice(0, 2)).toEqual(['-m', 'experiments.wilson_loop_3d.run']);
    expect(spec.args).toContain('--axes3');
    expect(spec.args).toContain('alpha');
    expect(spec.args).toContain('beta');
    expect(spec.args).toContain('gamma');
    expect(spec.args).toEqual(
      expect.arrayContaining([
        '--center',
        '0.1',
        '-0.2',
        '0.3',
        '--amplitudes',
        '0.4',
        '0.2',
        '0.1',
        '--steps',
        '48',
        '--handle-steps',
        '24',
        '--settle',
        '80',
        '--fs-guard',
        '0.18',
        '--graph',
        'ring3',
        '--seed',
        '11',
        '--eta-q',
        '0.5',
        '--zeta',
        '0.2',
        '--omega-scale',
        '1.25',
        '--output-dir',
        '/tmp/out',
      ]),
    );
  });

  it('switches to script strategy when requested', () => {
    const spec = cmdWilson3D('python3', {
      axes3: ['rho', 'tau', 'phi_custom'],
      center: [1, 2, 3],
      amplitudes: [0.1, 0.1, 0.0],
      steps: 32,
      strategy: 'script',
    });

    const expectedScript = path.join(
      __dirname,
      '..',
      '..',
      '..',
      'cwt-sim',
      'experiments',
      'wilson_loop_3d',
      'run.py',
    );

    expect(spec.args[0]).toBe(expectedScript);
    expect(spec.args).toContain('--steps');
    expect(spec.args).toContain('32');
  });
});

describe('cmdTorusPlateau', () => {
  it('builds commands aligned with torus plateau script', () => {
    const spec = cmdTorusPlateau('python', {
      axes: ['tau', 'zeta_phase'],
      gridSize: 33,
      disorderList: [0.0, 0.05, 0.1],
      centersExtents: {
        tau: { center: 0.3, extent: 0.25 },
        zeta_phase: { center: 0.45, extent: 0.55 },
      },
      outDir: '/tmp/torus',
    });

    expect(spec.command).toBe('python');
    expect(spec.args.slice(0, 2)).toEqual(['-m', 'experiments.torus_plateau.run']);
    expect(spec.args).toEqual(
      expect.arrayContaining([
        '--axes',
        'tau',
        'zeta_phase',
        '--grid-size',
        '33',
        '--disorder',
        '0',
        '0.05',
        '0.1',
        '--tau-center',
        '0.3',
        '--tau-extent',
        '0.25',
        '--zeta-center',
        '0.45',
        '--zeta-extent',
        '0.55',
        '--output-dir',
        '/tmp/torus',
      ]),
    );
  });

  it('falls back to defaults when configs are missing', () => {
    const spec = cmdTorusPlateau('python', {
      axes: ['tau', 'zeta'],
      centersExtents: [],
    });

    expect(spec.args).toEqual(
      expect.arrayContaining([
        '--tau-center',
        '0.28',
        '--tau-extent',
        '0.22',
        '--zeta-center',
        '0.5',
        '--zeta-extent',
        '0.5',
      ]),
    );
  });

  it('supports script execution strategy', () => {
    const spec = cmdTorusPlateau('python', {
      axes: ['tau', 'zeta'],
      centersExtents: [],
      strategy: 'script',
    });

    const expectedScript = path.join(
      __dirname,
      '..',
      '..',
      '..',
      'cwt-sim',
      'experiments',
      'torus_plateau',
      'run.py',
    );

    expect(spec.args[0]).toBe(expectedScript);
  });
});
