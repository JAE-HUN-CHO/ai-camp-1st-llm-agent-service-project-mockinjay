import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WelcomeMessage } from '../WelcomeMessage';

const agentFixtures = {
  auto: {
    message: '안녕하세요! 무엇이든 물어보세요. 최적의 전문가가 답변해 드립니다.',
    suggestions: ['신장병 환자를 위한 식단 추천해줘', '투석 환자 지원 제도 알려줘', 'CKD 최신 연구 동향은?'],
  },
  medical_welfare: {
    message: '안녕하세요! 신장병의 의료 복지 정보를 알려드리는 케어가이드 챗봇입니다. 무엇이든 물어보세요.',
    suggestions: ['신장병 환자를 위한 의료 복지 혜택은?', '투석 환자 지원 제도 알려줘'],
  },
  nutrition: {
    message: '안녕하세요! 신장병의 식이 영양 정보를 알려드리는 케어가이드 챗봇입니다. 무엇이든 물어보세요.',
    suggestions: ['저칼륨 음식 재료 알려줘', '신장병 환자를 위한 김장 레시피 알려줘'],
  },
  research: {
    message: '안녕하세요! 신장병의 연구 논문 정보를 알려드리는 케어가이드 챗봇입니다. 무엇이든 물어보세요.',
    suggestions: ['만성신장병 최신 연구 동향은?', 'CKD 치료법 관련 논문 찾아줘'],
  },
} as const;

describe('WelcomeMessage', () => {
  const onSuggestionClick = vi.fn();

  beforeEach(() => vi.clearAllMocks());

  it.each(Object.entries(agentFixtures))('renders the %s agent contract', (agentType, fixture) => {
    render(
      <WelcomeMessage
        agentType={agentType as keyof typeof agentFixtures}
        onSuggestionClick={onSuggestionClick}
      />
    );

    expect(screen.getByText('CareGuide AI')).toBeInTheDocument();
    expect(screen.getByRole('article', { name: /welcome message/i })).toHaveTextContent(fixture.message);
    fixture.suggestions.forEach((suggestion) => {
      expect(screen.getByRole('listitem', { name: `Suggestion: ${suggestion}` })).toBeInTheDocument();
    });
  });

  it('sends a selected suggestion', async () => {
    const user = userEvent.setup();
    render(<WelcomeMessage agentType="nutrition" onSuggestionClick={onSuggestionClick} />);

    const suggestion = agentFixtures.nutrition.suggestions[0];
    await user.click(screen.getByRole('listitem', { name: `Suggestion: ${suggestion}` }));

    expect(onSuggestionClick).toHaveBeenCalledWith(suggestion);
  });

  it('disables suggestions while the agent is busy', async () => {
    const user = userEvent.setup();
    render(<WelcomeMessage agentType="nutrition" onSuggestionClick={onSuggestionClick} isDisabled />);

    const suggestion = screen.getByRole('listitem', {
      name: `Suggestion: ${agentFixtures.nutrition.suggestions[0]}`,
    });
    expect(suggestion).toBeDisabled();
    await user.click(suggestion);
    expect(onSuggestionClick).not.toHaveBeenCalled();
  });

  it('exposes accessible message and suggestion regions', () => {
    render(<WelcomeMessage agentType="auto" onSuggestionClick={onSuggestionClick} />);

    expect(screen.getByRole('region', { name: /welcome message/i })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /suggestion chips/i })).toBeInTheDocument();
    expect(screen.getByRole('article', { name: /welcome message/i })).toHaveClass(
      'bg-white/80',
      'rounded-2xl'
    );
  });
});
