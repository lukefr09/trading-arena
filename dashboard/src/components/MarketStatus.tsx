/**
 * MarketStatus component - shows market open/closed status
 */

import { useEffect, useState } from 'react';

export function MarketStatus() {
  const [isOpen, setIsOpen] = useState(false);
  const [nextChange, setNextChange] = useState('');

  useEffect(() => {
    const checkMarketStatus = () => {
      const now = new Date();

      // Convert to ET
      const etOptions: Intl.DateTimeFormatOptions = {
        timeZone: 'America/New_York',
        hour: 'numeric',
        minute: 'numeric',
        hour12: false,
      };
      const etTime = new Intl.DateTimeFormat('en-US', etOptions).format(now);
      const [hour, minute] = etTime.split(':').map(Number);
      const currentMinutes = hour * 60 + minute;

      // Get day of week in ET
      const dayOptions: Intl.DateTimeFormatOptions = {
        timeZone: 'America/New_York',
        weekday: 'short',
      };
      const day = new Intl.DateTimeFormat('en-US', dayOptions).format(now);

      // Market hours: 9:30 AM - 4:00 PM ET, Mon-Fri
      const marketOpen = 9 * 60 + 30; // 9:30 AM
      const marketClose = 16 * 60; // 4:00 PM

      const isWeekday = !['Sat', 'Sun'].includes(day);
      const isDuringHours = currentMinutes >= marketOpen && currentMinutes < marketClose;
      const marketIsOpen = isWeekday && isDuringHours;

      setIsOpen(marketIsOpen);

      // Calculate next change
      if (marketIsOpen) {
        const minutesUntilClose = marketClose - currentMinutes;
        const hours = Math.floor(minutesUntilClose / 60);
        const mins = minutesUntilClose % 60;
        setNextChange(`Closes in ${hours}h ${mins}m`);
      } else if (isWeekday && currentMinutes < marketOpen) {
        const minutesUntilOpen = marketOpen - currentMinutes;
        const hours = Math.floor(minutesUntilOpen / 60);
        const mins = minutesUntilOpen % 60;
        setNextChange(`Opens in ${hours}h ${mins}m`);
      } else {
        setNextChange('Opens Monday 9:30 AM ET');
      }
    };

    checkMarketStatus();
    const interval = setInterval(checkMarketStatus, 60000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`market-status ${isOpen ? 'open' : 'closed'}`}>
      <div className="market-status-dot" />
      <span style={{ fontWeight: 500 }}>
        {isOpen ? 'MARKET OPEN' : 'MARKET CLOSED'}
      </span>
      <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
        {nextChange}
      </span>
    </div>
  );
}
