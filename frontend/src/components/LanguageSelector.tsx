import { LANGUAGES } from "../constants";
import type { Language } from "../types";

interface LanguageSelectorProps {
  selectedLanguage: Language;
  onLanguageChange: (language: Language) => void;
}

export function LanguageSelector({
  selectedLanguage,
  onLanguageChange,
}: LanguageSelectorProps) {
  return (
    <select
      id="language-select"
      aria-label="Language"
      value={selectedLanguage}
      onChange={(e) => onLanguageChange(e.target.value as Language)}
      className="rounded-lg border border-parchment-300/60 dark:border-walnut-700
                 bg-parchment-50/80 dark:bg-walnut-900/80 px-3 py-1.5 text-sm
                 font-medium text-walnut-800 dark:text-parchment-200
                 focus:outline-none focus:ring-2 focus:ring-parchment-400/40
                 dark:focus:ring-parchment-400/20 cursor-pointer
                 backdrop-blur-sm transition-colors"
    >
      {LANGUAGES.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.label}
        </option>
      ))}
    </select>
  );
}
