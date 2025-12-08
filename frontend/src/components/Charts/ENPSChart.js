import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const ENPSChart = ({ data, score }) => {
    // data expected: { promoters: 6, passives: 5, detractors: 4 }
    const chartData = [
        { name: 'Promoters', value: data.promoters, color: '#10b981' }, // Success color
        { name: 'Passives', value: data.passives, color: '#f59e0b' },   // Warning color
        { name: 'Detractors', value: data.detractors, color: '#ef4444' }, // Danger color
    ];

    return (
        <div className="card span-2" style={{ minHeight: '350px' }}>
            <h3 className="card-title" style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>eNPS Distribution </h3>
            <div style={{ width: '100%', height: '250px' }}>
                <ResponsiveContainer>
                    <PieChart>
                        <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                </ResponsiveContainer>
            </div>
            <div style={{ textAlign: 'center', marginTop: '-170px', marginBottom: '100px' }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    {score !== undefined && score !== null ? score.toFixed(2) : 'N/A'}
                </div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>eNPS Score</div>
            </div>
        </div>
    );
};

export default ENPSChart;
