import { Link } from 'react-router-dom';

export default function StatsCard({ title, value, icon: Icon, trend, to }) {
  const containerClass = `bg-white/90 border border-amber-100 rounded-2xl p-6 h-full ${to ? 'transition-transform hover:-translate-y-1 hover:shadow-lg cursor-pointer' : ''}`;
  const trendClass = `mt-2 text-sm font-semibold ${trend >= 0 ? 'text-teal-600' : 'text-rose-600'}`;
  
  const content = (
    <div className={containerClass}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">{title}</p>
          <p className="mt-3 text-4xl font-semibold text-slate-900">{value}</p>
          {trend && (
            <p className={trendClass}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
            </p>
          )}
        </div>
        {Icon && (
          <div className="bg-teal-50 rounded-2xl p-3 border border-teal-100">
            <Icon className="w-8 h-8 text-teal-600" />
          </div>
        )}
      </div>
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="block h-full">
        {content}
      </Link>
    );
  }

  return content;
}
