import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const StatCard = ({ title, value, subtext, trend, trendValue, icon: Icon, color }) => {
    return (
        <div className="stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ flex: 1 }}>
                    <h3 style={{
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        color: 'var(--text-secondary)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginBottom: '0.5rem'
                    }}>
                        {title}
                    </h3>
                    <div style={{
                        fontSize: '2rem',
                        fontWeight: '700',
                        color: 'var(--text-primary)',
                        lineHeight: '1'
                    }}>
                        {value}
                    </div>
                </div>
                {Icon && (
                    <div style={{
                        padding: '0.75rem',
                        borderRadius: '12px',
                        backgroundColor: `${color}15`,
                        color: color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <Icon size={24} strokeWidth={2} />
                    </div>
                )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
                {trend === 'up' && <TrendingUp size={16} color="var(--success)" />}
                {trend === 'down' && <TrendingDown size={16} color="var(--danger)" />}
                {trend === 'neutral' && <Minus size={16} color="var(--text-secondary)" />}

                <span style={{
                    color: trend === 'up' ? 'var(--success)' : trend === 'down' ? 'var(--danger)' : 'var(--text-secondary)',
                    fontWeight: '600'
                }}>
                    {trendValue}
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>{subtext}</span>
            </div>
        </div>
    );
};

export default StatCard;
