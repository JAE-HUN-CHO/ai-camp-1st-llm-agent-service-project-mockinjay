import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MyPageEnhanced from '../../features/account/MyPage';

const mockNavigate = vi.fn();
const mockLogout = vi.fn();

vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', username: 'testuser', email: 'test@example.com', fullName: '홍길동' },
    logout: mockLogout,
    isAuthenticated: true,
  }),
}));

vi.mock('../../hooks/useQuizStats', () => ({
  useQuizStats: () => ({
    stats: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../../services/api', () => ({
  getUserBookmarks: vi.fn().mockResolvedValue({ bookmarks: [] }),
  getUserPosts: vi.fn().mockResolvedValue({ posts: [] }),
  updateUserProfile: vi.fn().mockResolvedValue({}),
  updateHealthProfile: vi.fn().mockResolvedValue({}),
  updateUserPreferences: vi.fn().mockResolvedValue({}),
  removeBookmark: vi.fn().mockResolvedValue(true),
  deleteUserPost: vi.fn().mockResolvedValue(true),
}));

const renderPage = () => render(<BrowserRouter><MyPageEnhanced /></BrowserRouter>);

describe('MyPageEnhanced', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the canonical profile and menu sections', async () => {
    renderPage();

    expect(screen.getByRole('heading', { name: '마이페이지' })).toBeInTheDocument();
    expect(screen.getByText('홍길동')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '계정 설정' })).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: '프로필 정보' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument());
  });

  it('opens profile editing from the account menu', () => {
    renderPage();
    fireEvent.click(screen.getByRole('listitem', { name: '프로필 정보' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('requires confirmation before logging out and then navigates home', () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: '로그아웃' }));
    expect(screen.getByText('로그아웃 하시겠습니까?')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '로그아웃', exact: true })[1]);
    expect(mockLogout).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith('/main');
  });
});
