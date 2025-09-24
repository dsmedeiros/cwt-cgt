import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

type CommandRegistration = {
  handler: () => void;
  description: string;
};

type CommandContextValue = {
  registerRun: (registration: CommandRegistration | null) => void;
  registerAbort: (registration: CommandRegistration | null) => void;
  runDescription: string | null;
  abortDescription: string | null;
  status: string | null;
};

type CommandProviderProps = {
  children: ReactNode;
  onToggleTheme: () => void;
};

const CommandContext = createContext<CommandContextValue | undefined>(undefined);

const RUN_COMBO_LABEL = '⌥R';
const ABORT_COMBO_LABEL = '⌥A';
const THEME_COMBO_LABEL = '⌥T';

export const CommandProvider = ({ children, onToggleTheme }: CommandProviderProps) => {
  const runRef = useRef<CommandRegistration | null>(null);
  const abortRef = useRef<CommandRegistration | null>(null);
  const statusTimerRef = useRef<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [runDescription, setRunDescription] = useState<string | null>(null);
  const [abortDescription, setAbortDescription] = useState<string | null>(null);

  const clearStatusLater = useCallback(() => {
    if (statusTimerRef.current) {
      window.clearTimeout(statusTimerRef.current);
    }
    statusTimerRef.current = window.setTimeout(() => {
      setStatus(null);
      statusTimerRef.current = null;
    }, 4000);
  }, []);

  const publishStatus = useCallback(
    (message: string) => {
      setStatus(message);
      clearStatusLater();
    },
    [clearStatusLater],
  );

  const registerRun = useCallback((registration: CommandRegistration | null) => {
    runRef.current = registration;
    setRunDescription(registration?.description ?? null);
  }, []);

  const registerAbort = useCallback((registration: CommandRegistration | null) => {
    abortRef.current = registration;
    setAbortDescription(registration?.description ?? null);
  }, []);

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.repeat) {
        return;
      }
      if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === 'r') {
        event.preventDefault();
        const registration = runRef.current;
        if (registration?.handler) {
          registration.handler();
          publishStatus(`Run: ${registration.description} (${RUN_COMBO_LABEL})`);
        } else {
          publishStatus('Run shortcut pressed, but no action is registered.');
        }
      } else if (key === 'a') {
        event.preventDefault();
        const registration = abortRef.current;
        if (registration?.handler) {
          registration.handler();
          publishStatus(`Abort: ${registration.description} (${ABORT_COMBO_LABEL})`);
        } else {
          publishStatus('Abort shortcut pressed, but no action is registered.');
        }
      } else if (key === 't') {
        event.preventDefault();
        onToggleTheme();
        publishStatus(`Theme toggled (${THEME_COMBO_LABEL}).`);
      }
    };

    window.addEventListener('keydown', handleKeydown);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
      if (statusTimerRef.current) {
        window.clearTimeout(statusTimerRef.current);
      }
    };
  }, [onToggleTheme, publishStatus]);

  const value = useMemo(
    () => ({ registerRun, registerAbort, runDescription, abortDescription, status }),
    [abortDescription, registerAbort, registerRun, runDescription, status],
  );

  return <CommandContext.Provider value={value}>{children}</CommandContext.Provider>;
};

export const useCommandCenter = () => {
  const context = useContext(CommandContext);
  if (!context) {
    throw new Error('useCommandCenter must be used within CommandProvider');
  }
  return context;
};

export const useCommandRegistration = (
  registration: { run?: CommandRegistration | null; abort?: CommandRegistration | null },
) => {
  const context = useContext(CommandContext);

  useEffect(() => {
    if (!context) {
      return;
    }

    context.registerRun(registration.run ?? null);
    return () => context.registerRun(null);
  }, [context, registration.run]);

  useEffect(() => {
    if (!context) {
      return;
    }

    context.registerAbort(registration.abort ?? null);
    return () => context.registerAbort(null);
  }, [context, registration.abort]);
};

export const useCommandCombos = () => ({
  run: RUN_COMBO_LABEL,
  abort: ABORT_COMBO_LABEL,
  theme: THEME_COMBO_LABEL,
});
