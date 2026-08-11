/**
 * Enhanced MyPage Component with Modal Integration
 * CarePlus 마이페이지 - 모달 통합 버전
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  User,
  Settings,
  Bell,
  FileText,
  LogOut,
  Trophy,
  Target,
  TrendingUp,
  Heart,
  Shield,
  HelpCircle,
  Edit3,
  Camera,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../types/careguide-ia';
import { useQuizStats } from '../../hooks/useQuizStats';
import { QuizStatsSkeleton, ProfileCardSkeleton, MenuSectionSkeleton, HealthInfoSkeleton } from '../../components/mypage/shared/Skeleton';
import { QuizStatsError } from '../../components/mypage/shared/ErrorState';
import { QuizStatsEmpty, HealthProfileEmpty } from '../../components/mypage/shared/EmptyState';
import {
  updateUserProfile,
  updateHealthProfile,
  updateUserPreferences,
  getUserBookmarks,
  removeBookmark,
  getUserPosts,
  deleteUserPost,
  type UserProfileUpdateData,
  type HealthProfileUpdateData,
  type UserPreferencesUpdateData,
} from '../../services/api';

// Import modal components
import {
  ProfileEditModal,
  HealthProfileModal,
  SettingsModal,
  BookmarkedPapersModal,
  MyPostsModal,
} from '../../components/mypage/MyPageModals';

const MyPageEnhanced: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { stats: quizStats, isLoading, error, refetch } = useQuizStats(user?.id);
  const [pageVisible, setPageVisible] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Page enter animation
  useEffect(() => {
    const timer = setTimeout(() => setPageVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Modal state management
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isHealthModalOpen, setIsHealthModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [isBookmarksModalOpen, setIsBookmarksModalOpen] = useState(false);
  const [isPostsModalOpen, setIsPostsModalOpen] = useState(false);

  // Form submission state
  const [, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  // Data from API (no more mock data)
  const [bookmarkedPapers, setBookmarkedPapers] = useState<{
    id: string;
    title: string;
    authors: string;
    journal?: string;
    year?: string;
    bookmarkedAt: string;
  }[]>([]);
  const [myPosts, setMyPosts] = useState<{
    id: string;
    title: string;
    content: string;
    postType: 'BOARD' | 'CHALLENGE' | 'SURVEY';
    likes: number;
    commentCount: number;
    createdAt: string;
  }[]>([]);
  const [, setIsLoadingBookmarks] = useState(false);
  const [, setIsLoadingPosts] = useState(false);

  // Fetch bookmarks from API
  const fetchBookmarks = useCallback(async () => {
    if (!user?.id) return;
    setIsLoadingBookmarks(true);
    try {
      const response = await getUserBookmarks();
      // Transform API response to component format
      const papers = (response.bookmarks || []).map((b) => ({
        id: b.paperId,
        title: b.paperData?.title || 'Untitled',
        authors: b.paperData?.authors || '',
        journal: b.paperData?.journal,
        year: b.paperData?.year,
        bookmarkedAt: b.createdAt,
      }));
      setBookmarkedPapers(papers);
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error);
    } finally {
      setIsLoadingBookmarks(false);
    }
  }, [user?.id]);

  // Fetch user posts from API
  const fetchPosts = useCallback(async () => {
    if (!user?.id) return;
    setIsLoadingPosts(true);
    try {
      const response = await getUserPosts();
      setMyPosts(response.posts || []);
    } catch (error) {
      console.error('Failed to fetch posts:', error);
    } finally {
      setIsLoadingPosts(false);
    }
  }, [user?.id]);

  // Fetch data on mount
  useEffect(() => {
    fetchBookmarks();
    fetchPosts();
  }, [fetchBookmarks, fetchPosts]);

  // Announce stats update to screen readers
  useEffect(() => {
    if (quizStats) {
      const announcement = `퀴즈 통계가 업데이트되었습니다. 총 획득 점수 ${quizStats.totalScore}점, 완료한 퀴즈 ${quizStats.totalSessions}개`;
      const liveRegion = document.getElementById('quiz-stats-live-region-enhanced');
      if (liveRegion) {
        liveRegion.textContent = announcement;
      }
    }
  }, [quizStats]);

  // Handler functions with loading states
  const handleLogout = () => {
    setShowLogoutConfirm(true);
  };

  const confirmLogout = () => {
    logout();
    navigate(ROUTES.MAIN);
  };

  // Menu sections configuration
  const menuSections = useMemo(() => [
    {
      title: '계정 설정',
      items: [
        { icon: User, label: '프로필 정보', onClick: () => setIsProfileModalOpen(true), badge: undefined },
        { icon: Heart, label: '건강 프로필', onClick: () => setIsHealthModalOpen(true), badge: undefined },
        { icon: Settings, label: '환경 설정', onClick: () => setIsSettingsModalOpen(true), badge: undefined },
        { icon: Bell, label: '알림 설정', onClick: () => navigate('/notification-settings'), badge: undefined },
      ],
    },
    {
      title: '콘텐츠 및 활동',
      items: [
        { icon: FileText, label: '북마크한 논문', onClick: () => setIsBookmarksModalOpen(true), badge: bookmarkedPapers.length },
        { icon: FileText, label: '내 커뮤니티 게시글', onClick: () => setIsPostsModalOpen(true), badge: myPosts.length },
      ],
    },
    {
      title: '지원',
      items: [
        { icon: HelpCircle, label: '도움말 및 FAQ', onClick: () => navigate('/support'), badge: undefined },
        { icon: Shield, label: '개인정보 처리방침', onClick: () => navigate('/privacy'), badge: undefined },
      ],
    },
  ], [bookmarkedPapers.length, myPosts.length, navigate]);

  const handleProfileSave = async (data: UserProfileUpdateData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      await updateUserProfile(data);

      // Save profile to localStorage for real-time sync with ChatPage
      if (data.profile) {
        const profileMap: Record<string, string> = {
          'patient': '신장병 환우',
          'researcher': '연구자',
          'general': '일반인'
        };
        const userType = profileMap[data.profile] || '일반인';
        localStorage.setItem('userProfile', userType);
      }

      setSubmitSuccess('프로필이 성공적으로 업데이트되었습니다.');
      setTimeout(() => {
        setIsProfileModalOpen(false);
        setSubmitSuccess(null);
      }, 1500);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : '프로필 업데이트에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleHealthProfileSave = async (data: HealthProfileUpdateData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      await updateHealthProfile(data);
      setSubmitSuccess('건강 프로필이 성공적으로 업데이트되었습니다.');
      setTimeout(() => {
        setIsHealthModalOpen(false);
        setSubmitSuccess(null);
      }, 1500);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : '건강 프로필 업데이트에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSettingsSave = async (settings: UserPreferencesUpdateData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      await updateUserPreferences(settings);
      setSubmitSuccess('설정이 성공적으로 저장되었습니다.');
      setTimeout(() => {
        setIsSettingsModalOpen(false);
        setSubmitSuccess(null);
      }, 1500);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : '설정 저장에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveBookmark = async (paperId: string) => {
    // Optimistic UI update
    const previousPapers = [...bookmarkedPapers];
    setBookmarkedPapers((prev) => prev.filter((p) => p.id !== paperId));

    try {
      const success = await removeBookmark(paperId);
      if (!success) {
        // Restore on failure
        setBookmarkedPapers(previousPapers);
        setSubmitError('북마크 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('Failed to remove bookmark:', error);
      // Restore on failure
      setBookmarkedPapers(previousPapers);
      setSubmitError('북마크 삭제에 실패했습니다.');
    }
  };

  const handleDeletePost = async (postId: string) => {
    // Optimistic UI update
    const previousPosts = [...myPosts];
    setMyPosts((prev) => prev.filter((p) => p.id !== postId));

    try {
      const success = await deleteUserPost(postId);
      if (!success) {
        // Restore on failure
        setMyPosts(previousPosts);
        setSubmitError('게시글 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('Failed to delete post:', error);
      // Restore on failure
      setMyPosts(previousPosts);
      setSubmitError('게시글 삭제에 실패했습니다.');
    }
  };

  // User initials for avatar
  const userInitials = user?.fullName
    ? user.fullName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : user?.username?.substring(0, 2).toUpperCase() || 'U';

  // Quiz stats
  const totalQuizzesTaken = quizStats?.totalSessions || 0;
  const totalCorrect = quizStats?.correctAnswers || 0;
  const totalQuestions = quizStats?.totalQuestions || 0;
  const totalPoints = quizStats?.totalScore || 0;
  const accuracyRate = quizStats?.accuracyRate || 0;
  const currentStreak = quizStats?.currentStreak || 0;
  const bestStreak = quizStats?.bestStreak || 0;

  const hasQuizData = quizStats && totalQuizzesTaken > 0;

  // Show full page skeleton on initial load
  if (isLoading && !quizStats) {
    return (
      <div className="max-w-4xl mx-auto animate-fade-in">
        <div className="h-9 w-32 bg-gray-200 rounded animate-pulse mb-8"></div>
        <ProfileCardSkeleton />
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <MenuSectionSkeleton items={5} />
            <MenuSectionSkeleton items={2} />
          </div>
          <div className="space-y-6">
            <QuizStatsSkeleton />
            <HealthInfoSkeleton />
            <div className="h-12 bg-gray-200 rounded-xl animate-pulse"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`max-w-4xl mx-auto transition-all duration-500 ${
      pageVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
    }`}>
      {/* Screen reader live region for dynamic content */}
      <div id="quiz-stats-live-region-enhanced" className="sr-only" role="status" aria-live="polite" aria-atomic="true"></div>

      <h1 className="text-3xl font-bold text-gray-900 mb-8">마이페이지</h1>

      {/* Success/Error Messages */}
      {submitSuccess && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-4 text-green-800 shadow-sm animate-slide-down flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          {submitSuccess}
        </div>
      )}
      {submitError && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-800 shadow-sm animate-slide-down">
          {submitError}
        </div>
      )}

      {/* Enhanced Profile Card */}
      <section className="bg-white rounded-2xl shadow-soft border border-gray-100 overflow-hidden mb-8 transition-all hover:shadow-medium" aria-label="프로필 정보">
        <div className="p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
            {/* Avatar with edit button */}
            <div className="relative self-center sm:self-start">
              <div className="w-20 h-20 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center text-white text-2xl font-bold shadow-glow" role="img" aria-label={`${user?.fullName || user?.username || '사용자'} 프로필 이미지`}>
                {userInitials}
              </div>
              <button
                onClick={() => setIsProfileModalOpen(true)}
                className="absolute -bottom-1 -right-1 w-8 h-8 bg-white rounded-full shadow-md flex items-center justify-center border border-gray-200 hover:bg-gray-50 transition-colors touch-target"
                aria-label="프로필 사진 변경"
              >
                <Camera size={14} className="text-gray-600" />
              </button>
            </div>

            {/* User Info */}
            <div className="flex-1 text-center sm:text-left">
              <div className="flex items-center justify-center sm:justify-start gap-2">
                <h2 className="text-2xl font-bold text-gray-900">
                  {user?.fullName || user?.username || '사용자'}
                </h2>
                <button
                  onClick={() => setIsProfileModalOpen(true)}
                  className="p-1 text-gray-400 hover:text-primary transition-colors"
                  aria-label="프로필 수정"
                >
                  <Edit3 size={16} />
                </button>
              </div>
              <p className="text-gray-600">{user?.email || 'email@example.com'}</p>
              <div className="mt-3 flex flex-wrap gap-2 justify-center sm:justify-start">
                <span className="px-3 py-1 bg-primary/10 text-primary font-medium text-xs rounded-full" role="status">
                  {totalQuizzesTaken}개 퀴즈 완료
                </span>
                {currentStreak > 0 && (
                  <span className="px-3 py-1 bg-orange-100 text-orange-600 font-medium text-xs rounded-full">
                    {currentStreak}일 연속 학습중
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Left Column - Settings */}
        <div className="md:col-span-2 space-y-6">
          {/* Dynamic Menu Sections */}
          {menuSections.map((section, sectionIndex) => (
            <nav
              key={section.title}
              className="bg-white rounded-2xl shadow-soft border border-gray-100 overflow-hidden"
              aria-label={section.title}
              style={{ animationDelay: `${sectionIndex * 100}ms` }}
            >
              <h3 className="p-4 border-b border-gray-100 font-bold text-gray-900 bg-gray-50/50">
                {section.title}
              </h3>
              <div className="divide-y divide-gray-100" role="list">
                {section.items.map((item) => {
                  const IconComponent = item.icon;
                  return (
                    <MenuItem
                      key={item.label}
                      icon={<IconComponent size={20} />}
                      label={item.label}
                      onClick={item.onClick}
                      badge={item.badge}
                    />
                  );
                })}
              </div>
            </nav>
          ))}
        </div>

        {/* Right Column - Stats & Actions */}
        <div className="space-y-6">
          {/* Quiz Stats with Loading/Error/Empty States */}
          {isLoading ? (
            <QuizStatsSkeleton />
          ) : error ? (
            <QuizStatsError onRetry={refetch} />
          ) : !hasQuizData ? (
            <QuizStatsEmpty onStartQuiz={() => navigate('/quiz')} />
          ) : (
            <section className="bg-white rounded-2xl shadow-soft border border-gray-100 p-6" aria-labelledby="quiz-stats-heading-enhanced">
              <div className="flex items-center gap-2 mb-4">
                <Trophy className="text-primary" size={24} aria-hidden="true" />
                <h3 id="quiz-stats-heading-enhanced" className="font-bold text-gray-900">퀴즈 통계</h3>
              </div>

              {/* Total Points Card */}
              <div
                className="rounded-xl p-4 mb-4 bg-gradient-to-br from-primary to-secondary shadow-lg shadow-primary/20"
                role="region"
                aria-label="총 획득 점수"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-white" aria-label={`${totalPoints}점`}>{totalPoints}</div>
                    <div className="text-sm text-white/90">총 획득 점수</div>
                  </div>
                  <Trophy className="text-white/80" size={32} aria-hidden="true" />
                </div>
              </div>

              {/* Detailed Stats */}
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
                  <dt className="text-gray-600 flex items-center gap-2">
                    <Trophy size={16} className="text-primary" aria-hidden="true" />
                    완료한 퀴즈
                  </dt>
                  <dd className="font-semibold text-gray-900">{totalQuizzesTaken}개</dd>
                </div>

                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
                  <dt className="text-gray-600 flex items-center gap-2">
                    <Target size={16} className="text-secondary" aria-hidden="true" />
                    맞춘 문제
                  </dt>
                  <dd className="font-semibold text-gray-900">
                    {totalCorrect}/{totalQuestions}
                  </dd>
                </div>

                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
                  <dt className="text-gray-600 flex items-center gap-2">
                    <Target size={16} className="text-primary" aria-hidden="true" />
                    정답률
                  </dt>
                  <dd className="font-semibold text-primary">
                    {accuracyRate.toFixed(1)}%
                  </dd>
                </div>

                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
                  <dt className="text-gray-600 flex items-center gap-2">
                    <TrendingUp size={16} className="text-orange-500" aria-hidden="true" />
                    현재 연속
                  </dt>
                  <dd className="font-semibold text-orange-600">
                    {currentStreak}회
                    <span role="img" aria-label="불꽃"> 🔥</span>
                  </dd>
                </div>

                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
                  <dt className="text-gray-600 flex items-center gap-2">
                    <TrendingUp size={16} className="text-amber-500" aria-hidden="true" />
                    최고 연속
                  </dt>
                  <dd className="font-semibold text-amber-600">{bestStreak}회</dd>
                </div>
              </dl>
            </section>
          )}

          {/* Health Info Card with Empty State */}
          <HealthProfileEmpty onSetup={() => setIsHealthModalOpen(true)} />

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="w-full bg-red-50 text-red-600 py-3 px-4 rounded-xl font-medium hover:bg-red-100 transition-colors flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 min-h-[44px] touch-target"
            aria-label="로그아웃"
          >
            <LogOut size={18} className="mr-2" aria-hidden="true" /> 로그아웃
          </button>
        </div>
      </div>

      {/* Logout Confirmation Dialog */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in" onClick={() => setShowLogoutConfirm(false)}>
          <div
            className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6 animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
                <LogOut size={24} className="text-red-600" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">로그아웃 하시겠습니까?</h3>
              <p className="text-sm text-gray-500 mb-6">다시 로그인하면 모든 데이터를 확인할 수 있습니다.</p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowLogoutConfirm(false)}
                  className="flex-1 py-3 px-4 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors touch-target"
                >
                  취소
                </button>
                <button
                  onClick={confirmLogout}
                  className="flex-1 py-3 px-4 bg-red-500 text-white rounded-xl font-medium hover:bg-red-600 transition-colors touch-target"
                >
                  로그아웃
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <ProfileEditModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        user={{
          fullName: user?.fullName || '',
          email: user?.email || '',
          phone: '',
          birthDate: '',
        }}
        onSave={handleProfileSave}
      />

      <HealthProfileModal
        isOpen={isHealthModalOpen}
        onClose={() => setIsHealthModalOpen(false)}
        onSave={handleHealthProfileSave}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        onSave={handleSettingsSave}
      />

      <BookmarkedPapersModal
        isOpen={isBookmarksModalOpen}
        onClose={() => setIsBookmarksModalOpen(false)}
        papers={bookmarkedPapers}
        onRemoveBookmark={handleRemoveBookmark}
      />

      <MyPostsModal
        isOpen={isPostsModalOpen}
        onClose={() => setIsPostsModalOpen(false)}
        posts={myPosts}
        onDeletePost={handleDeletePost}
      />
    </div>
  );
};

// MenuItem Component with optional badge
const MenuItem: React.FC<{
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  badge?: number;
}> = ({ icon, label, onClick, badge }) => (
  <button
    onClick={onClick}
    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors text-left group focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary/20 min-h-[44px]"
    role="listitem"
    aria-label={badge ? `${label}, ${badge}개` : label}
  >
    <div className="flex items-center">
      <div className="text-gray-400 mr-4 group-hover:text-primary transition-colors" aria-hidden="true">
        {icon}
      </div>
      <span className="text-gray-700 font-medium group-hover:text-gray-900">
        {label}
      </span>
    </div>
    {badge !== undefined && badge > 0 && (
      <span className="px-2.5 py-0.5 bg-primary/10 text-primary text-xs font-semibold rounded-full" aria-hidden="true">
        {badge}
      </span>
    )}
  </button>
);

export default MyPageEnhanced;
