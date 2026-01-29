/**
 * Utility functions for the Trading Arena dashboard
 */

// Competition started Jan 28, 2025
const START_DATE = new Date('2025-01-28T00:00:00');

/**
 * Get current trading day (Day 1 = Jan 28, 2025)
 */
export function getCurrentDay(): number {
  const now = new Date();
  const diffTime = now.getTime() - START_DATE.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return diffDays + 1;
}

/**
 * Get current time formatted as "HH:MM AM/PM"
 */
export function getCurrentTime(): string {
  return new Date().toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Chicago', // Central Time
  });
}

/**
 * Format as "Day X • HH:MM AM/PM"
 */
export function formatDayTime(): string {
  return `Day ${getCurrentDay()} • ${getCurrentTime()}`;
}
