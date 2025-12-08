import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const StatCard = ({ title, value, subtext, trend, trendValue, icon: Icon, color }) => {
    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h3 className="card-title">{title}</h3>
                    <div className="card-value">{value}</div>
                </div>
                {Icon && (
                    <div style={{
                        padding: '0.5rem',
                        borderRadius: '50%',
                        backgroundColor: `${color}20`,
                        color: color
                    }}>
                        <Icon size={24} />
                    </div>
                )}
            </div>
            {(subtext || trend) && (
                <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
                    {trend === 'up' && <TrendingUp size={16} color="var(--success)" />}
                    {trend === 'down' && <TrendingDown size={16} color="var(--danger)" />}
                    {trend === 'neutral' && <Minus size={16} color="var(--text-secondary)" />}

                    <span style={{
                        color: trend === 'up' ? 'var(--success)' : trend === 'down' ? 'var(--danger)' : 'var(--text-secondary)',
                        fontWeight: 500
                    }}>
                        {trendValue}
                    </span>
                    <span style={{ color: 'var(--text-secondary)' }}>{subtext}</span>
                </div>
            )}
        </div>
    );
};

export default StatCard;
