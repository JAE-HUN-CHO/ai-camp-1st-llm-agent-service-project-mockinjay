import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import SignupPage from '../SignupPage';
import { AuthProvider } from '../../contexts/AuthContext';

vi.mock('../../services/api', () => ({
  default: {
    get: undefined,
    post: vi.fn(),
    defaults: { headers: { common: {} } },
  },
  checkEmailDuplicate: vi.fn(),
  checkNicknameDuplicate: vi.fn(),
}));

const renderSignup = () => render(
  <BrowserRouter>
    <AuthProvider>
      <SignupPage />
    </AuthProvider>
  </BrowserRouter>
);

const proceedThroughTerms = async () => {
  await waitFor(() => expect(screen.getByRole('heading', { name: '약관 동의' })).toBeInTheDocument());
  const checkboxes = screen.getAllByRole('checkbox');
  fireEvent.click(checkboxes[1]);
  fireEvent.click(checkboxes[2]);
  fireEvent.click(screen.getByRole('button', { name: '다음 단계로' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: '계정 정보' })).toBeInTheDocument());
};

describe('SignupPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('starts at the required terms step with four progress steps', async () => {
    const { container } = renderSignup();
    await waitFor(() => expect(screen.getByRole('heading', { name: '약관 동의' })).toBeInTheDocument());
    expect(container.querySelectorAll('.h-2')).toHaveLength(4);
    expect(screen.getAllByRole('checkbox')).toHaveLength(5);
    expect(screen.getByRole('button', { name: '다음 단계로' })).toBeDisabled();
  });

  it('requires both mandatory terms before moving to account information', async () => {
    renderSignup();
    await proceedThroughTerms();
    expect(screen.getByPlaceholderText('example@email.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('6자 이상 입력해주세요')).toBeInTheDocument();
  });

  it('validates account information before moving to personal information', async () => {
    renderSignup();
    await proceedThroughTerms();

    fireEvent.change(screen.getByPlaceholderText('example@email.com'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('6자 이상 입력해주세요'), { target: { value: 'password1' } });
    fireEvent.change(screen.getByPlaceholderText('비밀번호를 다시 입력해주세요'), { target: { value: 'password1' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 단계로' }));

    await waitFor(() => expect(screen.getByRole('heading', { name: '개인 정보' })).toBeInTheDocument());
  });

  it('moves through optional personal information to disease selection', async () => {
    renderSignup();
    await proceedThroughTerms();
    fireEvent.change(screen.getByPlaceholderText('example@email.com'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('6자 이상 입력해주세요'), { target: { value: 'password1' } });
    fireEvent.change(screen.getByPlaceholderText('비밀번호를 다시 입력해주세요'), { target: { value: 'password1' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 단계로' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: '개인 정보' })).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText('2자 이상 입력'), { target: { value: '케어가이드' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 단계로' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: '질환 정보' })).toBeInTheDocument());
    expect(screen.getByText('해당사항 없음 / 나중에 입력하기')).toBeInTheDocument();
  });

  it('provides accessible labels for the current step and navigation', async () => {
    renderSignup();
    await waitFor(() => expect(screen.getByRole('heading', { name: '약관 동의' })).toBeInTheDocument());
    expect(screen.getByRole('link', { name: '로그인하기' })).toBeInTheDocument();
    expect(screen.getAllByRole('checkbox').every((checkbox) => checkbox instanceof HTMLInputElement)).toBe(true);
  });
});
