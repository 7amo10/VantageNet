// Mock Recharts components for testing
import React from 'react';

export const PieChart = ({ children }: any) => (
  <div data-testid="pie-chart">{children}</div>
);

export const Pie = ({ data, dataKey }: any) => (
  <div data-testid="pie" data-key={dataKey}>
    {data?.map((item: any, index: number) => (
      <div key={index} data-testid={`pie-cell-${index}`}>
        {item[dataKey]}
      </div>
    ))}
  </div>
);

export const Cell = ({ fill }: any) => (
  <div data-testid="cell" data-fill={fill} />
);

export const Legend = () => <div data-testid="legend" />;

export const Tooltip = () => <div data-testid="tooltip" />;

export const ResponsiveContainer = ({ children }: any) => (
  <div data-testid="responsive-container">{children}</div>
);

export const LineChart = ({ children }: any) => (
  <div data-testid="line-chart">{children}</div>
);

export const Line = ({ dataKey, stroke }: any) => (
  <div data-testid="line" data-key={dataKey} data-stroke={stroke} />
);

export const BarChart = ({ children }: any) => (
  <div data-testid="bar-chart">{children}</div>
);

export const Bar = ({ dataKey, fill }: any) => (
  <div data-testid="bar" data-key={dataKey} data-fill={fill} />
);

export const XAxis = ({ dataKey }: any) => (
  <div data-testid="x-axis" data-key={dataKey} />
);

export const YAxis = () => <div data-testid="y-axis" />;

export const CartesianGrid = () => <div data-testid="cartesian-grid" />;

export const AreaChart = ({ children }: any) => (
  <div data-testid="area-chart">{children}</div>
);

export const Area = ({ dataKey, fill }: any) => (
  <div data-testid="area" data-key={dataKey} data-fill={fill} />
);
