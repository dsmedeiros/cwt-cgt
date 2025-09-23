import fs from 'fs';
import os from 'os';
import path from 'path';
import { SpawnSyncReturns } from 'child_process';

jest.mock('child_process', () => ({
  spawnSync: jest.fn(),
}));

jest.mock('../commands', () => ({
  cmdWilson3D: jest.fn(() => ({ cmd: 'python', args: ['script.py'], cwd: '/tmp' })),
}));

import { spawnSync } from 'child_process';
import { cmdWilson3D } from '../commands';
import { guidedLoop } from '../calibrator';

function createSpawnResult(stdout: string): SpawnSyncReturns<string> {
  return {
    pid: 123,
    output: [stdout, '', ''],
    stdout,
    stderr: '',
    status: 0,
    signal: null,
  } as SpawnSyncReturns<string>;
}

describe('guidedLoop', () => {
  const failFixture = fs.readFileSync(
    path.join(__dirname, '..', '__fixtures__', 'guided_loop_fail.txt'),
    'utf8'
  );
  const successFixture = fs.readFileSync(
    path.join(__dirname, '..', '__fixtures__', 'guided_loop_success.txt'),
    'utf8'
  );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns success when a later step meets guard requirements', () => {
    const spawnSyncMock = spawnSync as jest.MockedFunction<typeof spawnSync>;
    spawnSyncMock
      .mockReturnValueOnce(createSpawnResult(failFixture))
      .mockReturnValueOnce(createSpawnResult(successFixture));

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'guided-loop-'));

    const result = guidedLoop({
      pythonExe: 'python3',
      axes3: ['x', 'y', 'z'],
      center: [0, 0, 0],
      baseAmps: [0.2, 0.2, 0.1],
      outDir: tmpDir,
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.steps).toBe(320);
      expect(result.amps).toEqual([0.2, 0.2, 0.1]);
      expect(result.metrics.fsP95).toBeCloseTo(0.07);
      expect(result.metrics.phi).toBeCloseTo(0.02);
      expect(fs.readFileSync(result.out.stdout, 'utf8')).toBe(successFixture);
      expect(fs.existsSync(result.out.stderr)).toBe(true);
    }

    expect(spawnSyncMock).toHaveBeenCalledTimes(2);

    const commandCalls = (cmdWilson3D as jest.MockedFunction<typeof cmdWilson3D>).mock
      .calls;
    expect(commandCalls[0][1].steps).toBe(160);
    expect(commandCalls[1][1].steps).toBe(320);

    fs.rmSync(tmpDir, { recursive: true, force: true });
  });
});
