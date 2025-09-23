import fs from 'fs';
import os from 'os';
import path from 'path';

jest.mock('../../runner/commands', () => ({
  cmdLoopAtHotspot: jest.fn(() => ({ cmd: 'python', args: ['script.py'], cwd: '/repo' })),
  cmdAdiabaticBoundary: jest.fn(() => ({ cmd: 'python', args: ['adiabatic.py'], cwd: '/repo' })),
}));

jest.mock('../../runner/runner', () => ({
  createRun: jest.fn(() => 'mock-run-id'),
}));

jest.mock('../../runner/calibrator', () => ({
  guidedLoop: jest.fn(() => ({
    ok: true,
    amps: [0.2, 0.2, 0.1],
    steps: 320,
    metrics: { fsP95: 0.08, phi: 0.01 },
    out: { dir: '/tmp/attempt', stdout: '/tmp/attempt/stdout.txt', stderr: '/tmp/attempt/stderr.txt' },
  })),
}));

import { cmdLoopAtHotspot, cmdAdiabaticBoundary } from '../../runner/commands';
import { createRun } from '../../runner/runner';
import { guidedLoop as calibratorGuidedLoop } from '../../runner/calibrator';
import { loopAtHotspot, guidedLoop, adiabaticBoundary } from '../../ipc';

function createTempDir(prefix: string): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

describe('ipc handlers', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('loopAtHotspot', () => {
    it('writes hotspots JSON, spawns run, and returns metadata', async () => {
      const tempRoot = createTempDir('ipc-loop-');
      const outDir = path.join(tempRoot, 'workdir');
      const payload = {
        pythonExe: 'python3',
        hotspotsJson: '{"entries": 1}',
        axes: ['tau', 'zeta'] as [string, string],
        extents: [0.1, 0.2],
        fsGuard: 0.15,
        graph: 'ring3',
        limit: 3,
        seed: 42,
        strategy: 'script' as const,
        outDir,
      };

      (createRun as jest.Mock).mockReturnValue('loop-run-id');

      const result = await loopAtHotspot(payload);

      expect(result.runId).toBe('loop-run-id');
      expect(path.normalize(result.workdir)).toBe(path.resolve(outDir));

      const hotspotsPath = path.join(result.workdir, 'hotspots.json');
      expect(fs.existsSync(hotspotsPath)).toBe(true);
      const fileContent = fs.readFileSync(hotspotsPath, 'utf8');
      expect(() => JSON.parse(fileContent)).not.toThrow();

      expect(cmdLoopAtHotspot).toHaveBeenCalledTimes(1);
      const commandArgs = (cmdLoopAtHotspot as jest.Mock).mock.calls[0][1];
      expect(commandArgs.hotspots).toBe(hotspotsPath);
      expect(commandArgs.axes).toEqual(['tau', 'zeta']);
      expect(commandArgs.extents).toEqual([0.1, 0.2]);
      expect(commandArgs.fsGuard).toBe(0.15);
      expect(commandArgs.limit).toBe(3);
      expect(commandArgs.seed).toBe(42);

      expect(createRun).toHaveBeenCalledWith(
        expect.objectContaining({
          phase: 'phase3',
          experiment: 'loop_at_hotspot',
          cmd: 'python',
          args: ['script.py'],
          cwd: '/repo',
          seed: 42,
        })
      );

      fs.rmSync(tempRoot, { recursive: true, force: true });
    });

    it('throws a helpful error when hotspots JSON is invalid', async () => {
      await expect(
        loopAtHotspot({
          pythonExe: 'python3',
          hotspotsJson: '{',
          axes: ['tau', 'zeta'],
          extents: [0.1],
        })
      ).rejects.toThrow(/Unable to parse hotspotsJson/i);
    });
  });

  describe('guidedLoop', () => {
    it('normalizes options and delegates to the calibrator', () => {
      const tempRoot = createTempDir('ipc-guided-');
      const customOut = path.join(tempRoot, 'attempts');
      const payload = {
        pythonExe: 'python3',
        axes3: ['tau', 'zeta', 'rho'] as [string, string, string],
        center: [0, 0, 0] as [number, number, number],
        baseAmps: [0.2, 0.2, 0.1] as [number, number, number],
        stepsSeq: [160, 320],
        outDir: customOut,
      };

      const result = guidedLoop(payload);

      expect(result.ok).toBe(true);
      expect(fs.existsSync(path.resolve(customOut))).toBe(true);
      expect(calibratorGuidedLoop).toHaveBeenCalledWith(
        expect.objectContaining({
          pythonExe: 'python3',
          outDir: path.resolve(customOut),
          baseAmps: [0.2, 0.2, 0.1],
        })
      );

      fs.rmSync(tempRoot, { recursive: true, force: true });
    });

    it('creates a timestamped directory when outDir is not provided', () => {
      guidedLoop({
        pythonExe: 'python3',
        baseAmps: [0.1, 0.1, 0.1],
        outDir: undefined,
      });

      const call = (calibratorGuidedLoop as jest.Mock).mock.calls.slice(-1)[0][0];
      expect(call.outDir).toContain(path.join('artifacts', 'phase3', 'guided_loop'));
      fs.rmSync(call.outDir, { recursive: true, force: true });
      if (fs.existsSync(path.join('artifacts', 'phase3'))) {
        fs.rmSync(path.join('artifacts', 'phase3'), { recursive: true, force: true });
      }
    });
  });

  describe('adiabaticBoundary', () => {
    it('spawns the adiabatic boundary command and records the run', async () => {
      (createRun as jest.Mock).mockReturnValue('adiabatic-run');
      const tempRoot = createTempDir('ipc-adiabatic-');
      const outDir = path.join(tempRoot, 'boundary');

      const result = await adiabaticBoundary({
        pythonExe: 'python3',
        outDir,
        strategy: 'module',
      });

      expect(result.runId).toBe('adiabatic-run');
      expect(result.workdir).toBe(path.resolve(outDir));
      expect(cmdAdiabaticBoundary).toHaveBeenCalledWith(
        'python3',
        expect.objectContaining({
          outDir: path.resolve(outDir),
          strategy: 'module',
        })
      );
      expect(createRun).toHaveBeenCalledWith(
        expect.objectContaining({
          phase: 'phase3',
          experiment: 'adiabatic_boundary',
          cmd: 'python',
          args: ['adiabatic.py'],
        })
      );

      fs.rmSync(tempRoot, { recursive: true, force: true });
    });
  });
});
