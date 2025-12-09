import { render, screen } from '@testing-library/react';
import App from './App';

test('renders dashboard header', () => {
  render(<App />);
  const linkElement = screen.getByText(/Employee Survey Dashboard/i);
  expect(linkElement).toBeInTheDocument();
});
