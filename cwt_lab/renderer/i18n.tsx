import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

type MessageDictionary = Record<string, string>;

type I18nContextValue = {
  locale: string;
  setLocale: (locale: string) => void;
  t: (key: string, defaultMessage: string, values?: Record<string, string | number>) => string;
  messages: MessageDictionary;
};

const messagesByLocale: Record<string, MessageDictionary> = {
  en: {
    'app.title': 'CWT Lab',
    'app.demo.on': 'Demo: On',
    'app.demo.off': 'Demo: Off',
    'app.demo.hint': 'Toggle demo mode',
    'app.shortcuts.run': 'Run action',
    'app.shortcuts.abort': 'Abort action',
    'app.shortcuts.theme': 'Toggle theme',
    'app.demo.note': 'Demo mode is active',
    'app.shortcuts.none': 'No action registered',
  },
};

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

const interpolate = (template: string, values?: Record<string, string | number>) => {
  if (!values) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (_, token) => {
    const replacement = values[token];
    return replacement == null ? `{${token}}` : String(replacement);
  });
};

type I18nProviderProps = {
  children: ReactNode;
  defaultLocale?: string;
};

export const I18nProvider = ({ children, defaultLocale = 'en' }: I18nProviderProps) => {
  const [locale, setLocaleState] = useState(defaultLocale);

  const setLocale = useCallback((nextLocale: string) => {
    if (messagesByLocale[nextLocale]) {
      setLocaleState(nextLocale);
    }
  }, []);

  const t = useCallback(
    (key: string, defaultMessage: string, values?: Record<string, string | number>) => {
      const baseMessages = messagesByLocale[locale] ?? messagesByLocale.en;
      const message = baseMessages?.[key] ?? defaultMessage;
      return interpolate(message, values);
    },
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
      messages: messagesByLocale[locale] ?? messagesByLocale.en,
    }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useI18n = () => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
};

export const useTranslation = () => {
  const { t } = useI18n();
  return { t };
};

export const supportedLocales = Object.keys(messagesByLocale);
