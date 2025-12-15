
import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

export const TVChart = ({ data, color = '#2962FF' }) => {
    const chartContainerRef = useRef();
    const chartRef = useRef();
    const seriesRef = useRef();

    useEffect(() => {
        if (!chartContainerRef.current) return;

        let chart;
        const handleResize = () => {
             if (chartRef.current && chartContainerRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
             }
        };

        try {
            chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: 'transparent' },
                    textColor: '#64748b',
                },
                width: chartContainerRef.current.clientWidth || 300,
                height: 300,
                grid: {
                    vertLines: { color: 'rgba(51, 65, 85, 0.2)' },
                    horzLines: { color: 'rgba(51, 65, 85, 0.2)' },
                },
                timeScale: {
                    timeVisible: true,
                    secondsVisible: true,
                    borderColor: 'rgba(51, 65, 85, 0.4)',
                },
                rightPriceScale: {
                    borderColor: 'rgba(51, 65, 85, 0.4)',
                },
            });

            // Area Series
            const series = chart.addAreaSeries({
                lineColor: color,
                topColor: color,
                bottomColor: 'rgba(41, 98, 255, 0)',
                lineWidth: 2,
            });

            chartRef.current = chart;
            seriesRef.current = series;

            window.addEventListener('resize', handleResize);
        } catch (err) {
            console.error("TVChart Creation Error:", err);
        }

        return () => {
            window.removeEventListener('resize', handleResize);
            if (chart) {
                try {
                    chart.remove();
                } catch (e) {
                    console.error("Chart remove error", e);
                }
            }
        };
    }, [color]);

    // Update data
    useEffect(() => {
        if (seriesRef.current && data) {
            // Data is expected to be { time: seconds, price: number }
            const cleanData = data.map(d => ({
                time: d.time, 
                value: d.price
            })).filter((v, i, a) => i === 0 || v.time > a[i-1].time); // Ensure unique and sorted

            if (cleanData.length > 0) {
                 seriesRef.current.setData(cleanData);
            }
        }
    }, [data]);

    return (
        <div ref={chartContainerRef} className="w-full h-full" />
    );
};
