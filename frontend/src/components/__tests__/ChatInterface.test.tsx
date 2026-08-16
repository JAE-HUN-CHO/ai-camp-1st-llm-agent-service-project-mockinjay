import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ChatInterface from '../ChatInterface';
import { AuthProvider } from '../../contexts/AuthContext';
import { AppProvider } from '../../contexts/AppContext';
import { secureTokenStorage } from '../../utils/security';

// Mock the API
vi.mock('../../services/api', () => ({
  default: {
    post: vi.fn().mockResolvedValue({ data: { session_id: 'test-session' } }),
    defaults: {
      headers: {
        common: {},
      },
    },
  },
}));

// Mock fetch for streaming
global.fetch = vi.fn();

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <AppProvider>
      <AuthProvider>{component}</AuthProvider>
    </AppProvider>
  );
};

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    secureTokenStorage.clear();
  });

  describe('Profile Selector', () => {
    it('renders profile selector with default value', () => {
      renderWithProviders(<ChatInterface />);

      expect(screen.getByText('맞춤 정보:')).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toHaveValue('patient');
    });

    it('allows changing profile selection', async () => {
      renderWithProviders(<ChatInterface />);

      const select = screen.getByRole('combobox');

      fireEvent.change(select, { target: { value: 'general' } });

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toHaveValue('general');
      });
    });

    it('displays all profile options', () => {
      renderWithProviders(<ChatInterface />);

      const select = screen.getByRole('combobox');
      const options = select.querySelectorAll('option');

      expect(options).toHaveLength(3);
      expect(options[0]).toHaveTextContent('환자(신장병 환우)');
      expect(options[1]).toHaveTextContent('일반인(간병인)');
      expect(options[2]).toHaveTextContent('연구원');
    });
  });

  describe('Message Sending', () => {
    it('cancels and releases the reader after an invalid SSE frame', async () => {
      const cancel = vi.fn().mockResolvedValue(undefined);
      const releaseLock = vi.fn();
      const encoder = new TextEncoder();
      const read = vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode('data: {invalid json}\n\n'),
        })
        .mockResolvedValue({ done: true });
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: { getReader: () => ({ read, cancel, releaseLock }) },
      });

      renderWithProviders(<ChatInterface />);
      const input = screen.getByPlaceholderText(/만성콩팥병에 대해 무엇이든/i);
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(cancel).toHaveBeenCalledTimes(1);
        expect(releaseLock).toHaveBeenCalledTimes(1);
      });
    });

    it('includes user_profile in API payload', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        body: {
          getReader: () => ({
            read: vi.fn().mockResolvedValue({ done: true }),
          }),
        },
      });
      global.fetch = mockFetch;

      renderWithProviders(<ChatInterface />);

      const input = screen.getByPlaceholderText(/만성콩팥병에 대해 무엇이든/i);
      const sendButton = screen.getByRole('button');

      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            body: expect.stringContaining('user_profile'),
          })
        );
      });
    });

    it('forwards auth and CSRF headers to the real stream endpoint', async () => {
      secureTokenStorage.set('test-token', { memoryOnly: true });
      const mockFetch = vi.fn().mockResolvedValue({
        body: {
          getReader: () => ({
            read: vi.fn().mockResolvedValue({ done: true }),
          }),
        },
      });
      global.fetch = mockFetch;

      renderWithProviders(<ChatInterface />);
      const input = screen.getByPlaceholderText(/만성콩팥병에 대해 무엇이든/i);
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        const request = mockFetch.mock.calls[0][1];
        expect(request.headers.Authorization).toBe('Bearer test-token');
        expect(request.headers['X-CSRF-Token']).toBeTruthy();
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible profile selector', () => {
      renderWithProviders(<ChatInterface />);

      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
      expect(select).toHaveValue('patient');
    });

    it('maintains keyboard navigation', () => {
      renderWithProviders(<ChatInterface />);

      const select = screen.getByRole('combobox');

      select.focus();
      expect(document.activeElement).toBe(select);
    });
  });

  describe('Visual Feedback', () => {
    it('renders ChevronDown icon', () => {
      const { container } = renderWithProviders(<ChatInterface />);

      // ChevronDown icon should be present
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('uses correct color scheme', () => {
      renderWithProviders(<ChatInterface />);

      const profileLabel = screen.getByText('맞춤 정보:').nextElementSibling?.querySelector('span');
      expect(profileLabel).toBeTruthy();
      expect(profileLabel).toHaveClass('text-[#00c8b4]');
    });
  });
});
