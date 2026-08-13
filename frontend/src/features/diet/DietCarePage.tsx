import React, { useState, useEffect } from 'react';
import { useApp } from '../../contexts/AppContext';
import { useLocation, Link, useParams, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../types/careguide-ia';
import { ChefHat, BookOpen, ArrowLeft, Info, Target, TrendingUp } from 'lucide-react';

// 별도 컴포넌트 import
import { NutriCoachContent } from '../../components/diet-care/NutriCoachContent';
import { DietLogContent } from '../../components/diet-care/DietLogContent';
import { DietTypeDetailContent } from '../../components/diet-care/DietTypeDetailContent';
import { MobileHeader } from '../../components/layout/MobileHeader';
import { useAuth } from '../../contexts/AuthContext';
import { getDailyProgress, getStreak, getWeeklyProgress } from '../../services/dietCareApi';
import type { DailyProgressResponse, StreakResponse, WeeklyProgressResponse } from '../../types/diet-care';

// Quick stats component for diet overview
interface QuickStatProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: 'up' | 'down' | 'stable';
  color: string;
}

const QuickStat: React.FC<QuickStatProps> = ({ icon, label, value, trend, color }) => (
  <div className={`flex items-center gap-3 p-4 rounded-xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow ${color}`}>
    <div className="p-2 rounded-lg bg-gray-50">
      {icon}
    </div>
    <div className="flex-1">
      <p className="text-xs text-gray-500 font-medium">{label}</p>
      <div className="flex items-center gap-1">
        <span className="text-lg font-bold text-gray-900">{value}</span>
        {trend && (
          <TrendingUp
            size={14}
            className={`${
              trend === 'up' ? 'text-green-500' :
              trend === 'down' ? 'text-red-500 rotate-180' :
              'text-gray-400'
            }`}
          />
        )}
      </div>
    </div>
  </div>
);

const DietCarePageEnhanced: React.FC = () => {
  const { t, language } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const { dietType } = useParams<{ dietType: string }>();
  const [showTips, setShowTips] = useState(true);
  const [pageVisible, setPageVisible] = useState(false);
  const { user } = useAuth();
  const [dailyProgress, setDailyProgress] = useState<DailyProgressResponse | null>(null);
  const [weeklyProgress, setWeeklyProgress] = useState<WeeklyProgressResponse | null>(null);
  const [streak, setStreak] = useState<StreakResponse | null>(null);
  const [progressLoading, setProgressLoading] = useState(false);
  const [progressError, setProgressError] = useState<string | null>(null);

  // Page enter animation
  useEffect(() => {
    const timer = setTimeout(() => setPageVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // 현재 경로 판단
  const isNutriCoach = location.pathname === ROUTES.NUTRI_COACH || location.pathname === ROUTES.DIET_CARE;
  const isDietLog = location.pathname === ROUTES.DIET_LOG;
  const isDietTypeDetail = location.pathname.startsWith('/diet-care/diet-type/');

  useEffect(() => {
    setDailyProgress(null);
    setWeeklyProgress(null);
    setStreak(null);
    setProgressError(null);
    if (!user?.id || !isDietLog) {
      setProgressLoading(false);
      return;
    }
    let cancelled = false;
    setProgressLoading(true);
    Promise.all([getDailyProgress(), getWeeklyProgress(), getStreak()])
      .then(([daily, weekly, currentStreak]) => {
        if (cancelled) return;
        setDailyProgress(daily);
        setWeeklyProgress(weekly);
        setStreak(currentStreak);
        setProgressError(null);
      })
      .catch((error) => {
        if (!cancelled) setProgressError(error instanceof Error ? error.message : '식단 진행도를 불러오지 못했습니다.');
      })
      .finally(() => { if (!cancelled) setProgressLoading(false); });
    return () => { cancelled = true; };
  }, [user?.id, isDietLog]);

  // Tab configuration
  const tabs = [
    {
      id: 'nutri-coach',
      path: ROUTES.NUTRI_COACH,
      icon: ChefHat,
      label: t.nav.nutriCoach,
      description: language === 'ko' ? '영양 정보 및 식단 가이드' : 'Nutrition info & diet guide',
      isActive: isNutriCoach,
    },
    {
      id: 'diet-log',
      path: ROUTES.DIET_LOG,
      icon: BookOpen,
      label: t.nav.dietLog,
      description: language === 'ko' ? '식사 기록 및 분석' : 'Meal tracking & analysis',
      isActive: isDietLog,
    },
  ];

  // 상세 페이지인 경우
  if (isDietTypeDetail && dietType) {
    return (
      <div className="max-w-6xl mx-auto">
        {/* Mobile Header for Detail View */}
        <div className="lg:hidden">
          <MobileHeader 
            title={language === 'ko' ? '식단 상세' : 'Diet Detail'} 
            showMenu={false} 
            showProfile={false}
            onBack={() => navigate(ROUTES.NUTRI_COACH)}
          />
        </div>

        {/* 뒤로가기 버튼 (Desktop) */}
        <Link
          to={ROUTES.NUTRI_COACH}
          className="hidden lg:inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 mb-6 transition-colors"
        >
          <ArrowLeft size={20} />
          {language === 'ko' ? '뉴트리 코치로 돌아가기' : 'Back to Nutri Coach'}
        </Link>

        <DietTypeDetailContent dietType={dietType} language={language} />
      </div>
    );
  }

  // 메인 페이지
  return (
    <div className={`max-w-6xl mx-auto transition-all duration-500 ${
      pageVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
    }`}>
      {/* Mobile Header */}
      <div className="lg:hidden">
        <MobileHeader
          title={t.nav.dietCare}
          showMenu={true}
          showProfile={true}
        />
      </div>

      {/* Header with Tips Banner */}
      <div className="mb-6 hidden lg:block">
        <h1 className="text-4xl font-bold mb-2 text-gray-900 dark:text-white">
          {t.nav.dietCare}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          {language === 'ko'
            ? '만성콩팥병 환자를 위한 식단 관리 및 영양 정보'
            : 'Diet management and nutrition information for CKD patients'}
        </p>
      </div>

      {/* Tips Banner (dismissible) */}
      {showTips && (
        <div className="mb-6 p-4 bg-gradient-to-r from-primary/5 to-secondary/5 border border-primary/10 rounded-xl flex items-start gap-3 animate-fade-in">
          <Info size={20} className="text-primary flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-gray-700 leading-relaxed">
              {language === 'ko'
                ? '식사 사진을 업로드하면 AI가 영양소를 분석해드립니다. 정확한 분석을 위해 음식이 잘 보이도록 촬영해주세요.'
                : 'Upload a photo of your meal and our AI will analyze the nutrients. For accurate analysis, make sure the food is clearly visible.'}
            </p>
          </div>
          <button
            onClick={() => setShowTips(false)}
            className="text-gray-400 hover:text-gray-600 p-1"
            aria-label="닫기"
          >
            <span className="text-lg leading-none">&times;</span>
          </button>
        </div>
      )}

      {/* Enhanced Tab Navigation */}
      <nav className="mb-8" aria-label="식단 관리 탭">
        <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl">
          {tabs.map((tab) => {
            const IconComponent = tab.icon;
            return (
              <Link
                key={tab.id}
                to={tab.path}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-all touch-target ${
                  tab.isActive
                    ? 'bg-white dark:bg-gray-700 text-primary shadow-sm font-semibold'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-white/50'
                }`}
                aria-current={tab.isActive ? 'page' : undefined}
              >
                <IconComponent size={20} />
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden text-sm">{tab.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Active Tab Description */}
        <p className="mt-2 text-center text-sm text-gray-500">
          {tabs.find(t => t.isActive)?.description}
        </p>
      </nav>

      {/* Quick Stats Overview (only for Diet Log) */}
      {isDietLog && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6 animate-fade-in">
          {progressError && <p className="col-span-full text-sm text-red-600">{progressError}</p>}
          <QuickStat
            icon={<Target size={18} className="text-primary" />}
            label={language === 'ko' ? '오늘 칼로리' : 'Today Calories'}
            value={progressLoading ? '...' : `${Math.round(dailyProgress?.calories.current || 0).toLocaleString()} kcal`}
            trend="stable"
            color="hover:border-primary/30"
          />
          <QuickStat
            icon={<ChefHat size={18} className="text-green-500" />}
            label={language === 'ko' ? '식사 기록' : 'Meals Logged'}
            value={progressLoading ? '...' : `${dailyProgress?.meals_logged || 0}/${dailyProgress?.total_meals || 3}`}
            color="hover:border-green-300"
          />
          <QuickStat
            icon={<TrendingUp size={18} className="text-blue-500" />}
            label={language === 'ko' ? '주간 목표' : 'Weekly Goal'}
            value={progressLoading ? '...' : `${Math.round(weeklyProgress?.average_compliance || 0)}%`}
            trend="up"
            color="hover:border-blue-300"
          />
          <QuickStat
            icon={<BookOpen size={18} className="text-purple-500" />}
            label={language === 'ko' ? '연속 기록' : 'Streak'}
            value={progressLoading ? '...' : `${streak?.current_streak || 0}${language === 'ko' ? '일' : ' days'}`}
            color="hover:border-purple-300"
          />
        </div>
      )}

      {/* Content - 별도 컴포넌트 사용 */}
      <div className="animate-fade-in" style={{ animationDelay: '100ms' }}>
        {isNutriCoach && <NutriCoachContent language={language} />}
        {isDietLog && <DietLogContent language={language} />}
      </div>
    </div>
  );
};

export default DietCarePageEnhanced;
