import { Link } from 'react-router-dom';

export default function StatsCard({ title, value, icon: Icon, trend, to }) {
  const containerClass = `bg-white rounded-lg shadow-md p-6 h-full ${to ? 'transition-transform hover:-translate-y-1 hover:shadow-lg cursor-pointer' : ''}`;
  const trendClass = `mt-2 text-sm ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`;
  
  const content = (
    <div className={containerClass}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
          {trend && (
            <p className={trendClass}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
            </p>
          )}
        </div>
        {Icon && (
          <div className="bg-blue-50 rounded-full p-3">
            <Icon className="w-8 h-8 text-blue-600" />
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
