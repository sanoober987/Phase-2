// frontend/lib/utils.ts

import { ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind + conditional class names safely
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Generate a unique ID string (for toasts, notifications, etc.)
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 9) + Date.now().toString(36);
}

/**
 * Validate an email address format.
 */
export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Format a timestamp as relative time (e.g., "3 minutes ago").
 */
export function formatRelativeTime(date: string | number | Date): string {
  const d = new Date(date);
  const now = new Date();
  const diff = (d.getTime() - now.getTime()) / 1000; // difference in seconds

  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  const absDiff = Math.abs(diff);

  if (absDiff < 60) {
    return rtf.format(Math.round(diff), "seconds");
  } else if (absDiff < 3600) {
    return rtf.format(Math.round(diff / 60), "minutes");
  } else if (absDiff < 86400) {
    return rtf.format(Math.round(diff / 3600), "hours");
  } else if (absDiff < 2592000) {
    return rtf.format(Math.round(diff / 86400), "days");
  } else if (absDiff < 31536000) {
    return rtf.format(Math.round(diff / 2592000), "months");
  } else {
    return rtf.format(Math.round(diff / 31536000), "years");
  }
}
