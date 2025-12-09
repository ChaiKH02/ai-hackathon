import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const TrendChart = ({ data, lines, title, filters }) => {

    // Format tooltip value
    const formatValue = (value) => {
        if (typeof value === 'number') {
            return value.toFixed(1);
        }
        return value;
    };

    return (
        <div className="card" style={{ minHeight: '350px', gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 className="card-title" style={{ fontSize: '1.1rem', marginBottom: 0 }}>
                    {title}
                </h3>
                {filters && (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {filters}
                    </div>
                )}
            </div>
            <div style={{ width: '100%', height: '280px' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                        data={data}
                        margin={{
                            top: 5,
                            right: 30,
                            left: 0,
                            bottom: 5,
                        }}
                    >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="Quarter" />
                        <YAxis domain={[0, 'auto']} />
                        <Tooltip
                            shared={false}
                            formatter={(value) => formatValue(value)}
                            labelStyle={{ color: '#333' }}
                        />
                        <Legend />
                        {lines.map((line, index) => (
                            <Line
                                key={line.key}
                                type="monotone"
                                dataKey={line.key}
                                name={line.name}
                                stroke={line.color}
                                strokeWidth={3}
                                dot={{ r: 5, fill: line.color }}
                                activeDot={{ r: 8 }}
                                connectNulls={true}
                                isAnimationActive={true}
                                animationDuration={1500}
                                animationEasing="ease-in-out"
                            />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default TrendChart;
