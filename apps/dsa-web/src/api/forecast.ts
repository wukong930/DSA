import apiClient from './index';

export interface ForecastData {
  stockCode: string;
  horizonDays: number;
  predictedPrices: number[];
  lowerBound: number[];
  upperBound: number[];
  trend: 'up' | 'down' | 'neutral';
  trendPct: number;
  lastClose: number;
  modelVersion: string;
}

export const forecastApi = {
  getForecast: async (stockCode: string, horizon: number = 5): Promise<ForecastData> => {
    const res = await apiClient.get<Record<string, unknown>>(`/api/v1/forecast/${stockCode}`, {
      params: { horizon },
    });
    const d = res.data;
    return {
      stockCode: d.stock_code as string,
      horizonDays: d.horizon_days as number,
      predictedPrices: d.predicted_prices as number[],
      lowerBound: d.lower_bound as number[],
      upperBound: d.upper_bound as number[],
      trend: d.trend as ForecastData['trend'],
      trendPct: d.trend_pct as number,
      lastClose: d.last_close as number,
      modelVersion: d.model_version as string,
    };
  },
};
