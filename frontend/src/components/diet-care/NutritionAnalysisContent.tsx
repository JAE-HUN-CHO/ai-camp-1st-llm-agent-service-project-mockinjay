/**
 * NutritionAnalysisContent Component
 * Displays nutrition analysis with charts and insights
 */

import React, { useState, useMemo } from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  ArrowRight,
  Droplets,
  Flame,
  Beef,
  Pill,
  Leaf
} from 'lucide-react';
import { useEffect } from 'react';
import { getGoals, getWeeklyProgress } from '../../services/dietCareApi';
import type { NutritionGoals } from '../../types/diet-care';

export interface NutritionAnalysisContentProps {
  language: 'en' | 'ko';
}

interface NutrientData {
  name: string;
  nameEn: string;
  current: number;
  goal: number;
  unit: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  trend: 'up' | 'down' | 'stable';
  trendPercent: number;
}

interface WeeklyData {
  day: string;
  dayEn: string;
  calories: number;
  protein: number;
  sodium: number;
  potassium: number;
  phosphorus: number;
}

type ChartDataKey = keyof Omit<WeeklyData, 'day' | 'dayEn'>;
const NUTRITION_PROGRESS_ERROR = 'nutrition_progress_load_error';

const SimpleBarChart: React.FC<{
  data: WeeklyData[];
  dataKey: ChartDataKey;
  goal: number;
  color: string;
  isKo: boolean;
}> = ({ data, dataKey, goal, color, isKo }) => {
  const maxValue = Math.max(...data.map((d) => d[dataKey]), goal * 1.2, 1);

  return (
    <div className="relative flex items-end gap-1 h-32">
      {data.map((item, idx) => {
        const value = item[dataKey];
        const height = (value / maxValue) * 100;
        const isOverGoal = goal > 0 && value > goal;

        return (
          <div key={idx} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`w-full rounded-t transition-all ${isOverGoal ? 'bg-red-400' : color}`}
              style={{ height: `${height}%` }}
              title={`${value}`}
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {isKo ? item.day : item.dayEn}
            </span>
          </div>
        );
      })}
      {goal > 0 && (
        <div
          className="absolute left-0 right-0 border-t-2 border-dashed border-gray-400"
          style={{ bottom: `${(goal / maxValue) * 100}%` }}
        />
      )}
    </div>
  );
};

export const NutritionAnalysisContent: React.FC<NutritionAnalysisContentProps> = ({ language }) => {
  const [weeklyData, setWeeklyData] = useState<WeeklyData[]>([]);
  const [goals, setGoals] = useState<NutritionGoals | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [totalMealsLogged, setTotalMealsLogged] = useState<number | null>(null);
  const isKo = language === 'ko';
  const hasRecordedMeals = (totalMealsLogged ?? 0) > 0;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getWeeklyProgress(), getGoals()])
      .then(([weekly, goalResponse]) => {
        if (!active) return;
        const koreanDays = ['일', '월', '화', '수', '목', '금', '토'];
        const englishDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        setWeeklyData(weekly.daily_summaries.map((summary) => {
          const weekday = new Date(`${summary.date}T00:00:00`).getDay();
          return {
          day: koreanDays[weekday] || summary.date,
          dayEn: englishDays[weekday] || summary.date,
          calories: summary.total_calories,
          protein: summary.total_protein_g,
          sodium: summary.total_sodium_mg,
          potassium: summary.total_potassium_mg,
          phosphorus: summary.total_phosphorus_mg,
          };
        }));
        setTotalMealsLogged(weekly.total_meals_logged ?? null);
        setGoals(goalResponse.goals);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : NUTRITION_PROGRESS_ERROR);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // Calculate averages and current nutrient status
  const nutrientData: NutrientData[] = useMemo(() => {
    if (!goals || weeklyData.length === 0) return [];
    const divisor = weeklyData.length;
    const avgCalories = Math.round(weeklyData.reduce((sum, d) => sum + d.calories, 0) / divisor);
    const avgProtein = Math.round(weeklyData.reduce((sum, d) => sum + d.protein, 0) / divisor);
    const avgSodium = Math.round(weeklyData.reduce((sum, d) => sum + d.sodium, 0) / divisor);
    const avgPotassium = Math.round(weeklyData.reduce((sum, d) => sum + d.potassium, 0) / divisor);
    const avgPhosphorus = Math.round(weeklyData.reduce((sum, d) => sum + d.phosphorus, 0) / divisor);

    return [
      {
        name: '칼로리',
        nameEn: 'Calories',
        current: avgCalories,
        goal: goals.calories_kcal || 0,
        unit: 'kcal',
        icon: Flame,
        color: 'text-orange-500',
        bgColor: 'bg-orange-50 dark:bg-orange-900/20',
        trend: avgCalories > (goals.calories_kcal || 0) * 1.05 ? 'up' : avgCalories < (goals.calories_kcal || 0) * 0.95 ? 'down' : 'stable',
        trendPercent: goals.calories_kcal > 0 ? Math.round(((avgCalories - goals.calories_kcal) / goals.calories_kcal) * 100) : 0,
      },
      {
        name: '단백질',
        nameEn: 'Protein',
        current: avgProtein,
        goal: goals.protein_g || 0,
        unit: 'g',
        icon: Beef,
        color: 'text-red-500',
        bgColor: 'bg-red-50 dark:bg-red-900/20',
        trend: avgProtein > (goals.protein_g || 0) * 1.05 ? 'up' : avgProtein < (goals.protein_g || 0) * 0.95 ? 'down' : 'stable',
        trendPercent: goals.protein_g > 0 ? Math.round(((avgProtein - goals.protein_g) / goals.protein_g) * 100) : 0,
      },
      {
        name: '나트륨',
        nameEn: 'Sodium',
        current: avgSodium,
        goal: goals.sodium_mg || 0,
        unit: 'mg',
        icon: Droplets,
        color: 'text-blue-500',
        bgColor: 'bg-blue-50 dark:bg-blue-900/20',
        trend: avgSodium > (goals.sodium_mg || 0) * 1.05 ? 'up' : avgSodium < (goals.sodium_mg || 0) * 0.95 ? 'down' : 'stable',
        trendPercent: goals.sodium_mg > 0 ? Math.round(((avgSodium - goals.sodium_mg) / goals.sodium_mg) * 100) : 0,
      },
      {
        name: '칼륨',
        nameEn: 'Potassium',
        current: avgPotassium,
        goal: goals.potassium_mg || 0,
        unit: 'mg',
        icon: Leaf,
        color: 'text-green-500',
        bgColor: 'bg-green-50 dark:bg-green-900/20',
        trend: avgPotassium > (goals.potassium_mg || 0) * 1.05 ? 'up' : avgPotassium < (goals.potassium_mg || 0) * 0.95 ? 'down' : 'stable',
        trendPercent: goals.potassium_mg > 0 ? Math.round(((avgPotassium - goals.potassium_mg) / goals.potassium_mg) * 100) : 0,
      },
      {
        name: '인',
        nameEn: 'Phosphorus',
        current: avgPhosphorus,
        goal: goals.phosphorus_mg || 0,
        unit: 'mg',
        icon: Pill,
        color: 'text-purple-500',
        bgColor: 'bg-purple-50 dark:bg-purple-900/20',
        trend: avgPhosphorus > (goals.phosphorus_mg || 0) * 1.05 ? 'up' : avgPhosphorus < (goals.phosphorus_mg || 0) * 0.95 ? 'down' : 'stable',
        trendPercent: goals.phosphorus_mg > 0 ? Math.round(((avgPhosphorus - goals.phosphorus_mg) / goals.phosphorus_mg) * 100) : 0,
      },
    ];
  }, [goals, weeklyData]);

  // Generate insights
  const insights = useMemo(() => {
    const results: { type: 'warning' | 'success' | 'info'; message: string; messageEn: string }[] = [];

    nutrientData.forEach(nutrient => {
      if (nutrient.goal <= 0) return;
      const percentage = (nutrient.current / nutrient.goal) * 100;

      if (percentage > 110) {
        results.push({
          type: 'warning',
          message: `${nutrient.name} 섭취량이 목표치를 ${Math.round(percentage - 100)}% 초과했습니다. 섭취량 조절이 필요합니다.`,
          messageEn: `${nutrient.nameEn} intake exceeds target by ${Math.round(percentage - 100)}%. Consider reducing intake.`,
        });
      } else if (percentage >= 90 && percentage <= 110) {
        results.push({
          type: 'success',
          message: `${nutrient.name} 섭취량이 목표 범위 내에 있습니다. 잘 관리하고 계십니다!`,
          messageEn: `${nutrient.nameEn} intake is within target range. Great job managing your diet!`,
        });
      }
    });

    return results;
  }, [nutrientData]);

  return (
    <div className="space-y-6">
      {error && <div className="p-4 rounded-lg bg-red-50 text-red-700">{error === NUTRITION_PROGRESS_ERROR ? (isKo ? '영양 진행도를 불러오지 못했습니다.' : 'Failed to load nutrition progress.') : error}</div>}
      {loading && <div className="p-4 rounded-lg bg-gray-50 text-gray-500">{isKo ? '영양 데이터를 불러오는 중...' : 'Loading nutrition data...'}</div>}
      {!loading && !error && totalMealsLogged === 0 && <div className="p-4 rounded-lg bg-gray-50 text-gray-500">{isKo ? '기록된 식단 데이터가 없습니다.' : 'No recorded diet data.'}</div>}
      {/* Period Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2 text-gray-900 dark:text-white">
          <BarChart3 className="text-blue-500" size={24} />
          {isKo ? '영양 분석' : 'Nutrition Analysis'}
        </h2>
        <div className="flex gap-2">
          <span className="px-4 py-2 rounded-lg font-medium bg-blue-600 text-white">
            {isKo ? '주간' : 'Weekly'}
          </span>
        </div>
      </div>

      {/* Nutrient Summary Cards */}
      {!loading && !error && hasRecordedMeals && weeklyData.length > 0 && goals && <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {nutrientData.filter((nutrient) => nutrient.goal > 0).map(nutrient => {
          const NutrientIcon = nutrient.icon;
          const percentage = Math.round((nutrient.current / nutrient.goal) * 100);
          const isOverGoal = percentage > 100;

          return (
            <div
              key={nutrient.name}
              className={`${nutrient.bgColor} p-4 rounded-xl`}
            >
              <div className="flex items-center justify-between mb-2">
                <NutrientIcon className={nutrient.color} size={24} />
                <div className="flex items-center gap-1">
                  {nutrient.trend === 'up' && <TrendingUp className="text-red-500" size={16} />}
                  {nutrient.trend === 'down' && <TrendingDown className="text-green-500" size={16} />}
                  <span className={`text-sm font-medium ${
                    nutrient.trendPercent > 0 ? 'text-red-500' : 'text-green-500'
                  }`}>
                    {nutrient.trendPercent > 0 ? '+' : ''}{nutrient.trendPercent}%
                  </span>
                </div>
              </div>
              <h3 className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                {isKo ? nutrient.name : nutrient.nameEn}
              </h3>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {nutrient.current.toLocaleString()}
                </span>
                <span className="text-sm text-gray-500">{nutrient.unit}</span>
              </div>
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>{isKo ? '목표' : 'Goal'}: {nutrient.goal.toLocaleString()}</span>
                  <span className={isOverGoal ? 'text-red-500 font-medium' : ''}>
                    {percentage}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isOverGoal ? 'bg-red-500' : nutrient.color.replace('text-', 'bg-')
                    }`}
                    style={{ width: `${Math.min(percentage, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>}

      {/* Weekly Trend Charts */}
      {!loading && !error && hasRecordedMeals && weeklyData.length > 0 && goals && <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
          <Calendar className="text-blue-500" size={20} />
          {isKo ? '주간 섭취량 추이' : 'Weekly Intake Trends'}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Calories Chart */}
          <div>
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-2">
              <Flame className="text-orange-500" size={16} />
              {isKo ? '칼로리' : 'Calories'}
            </h4>
            <div className="relative h-36 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <SimpleBarChart data={weeklyData} dataKey="calories" goal={goals.calories_kcal || 0} color="bg-orange-400" isKo={isKo} />
            </div>
          </div>

          {/* Sodium Chart */}
          <div>
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-2">
              <Droplets className="text-blue-500" size={16} />
              {isKo ? '나트륨' : 'Sodium'}
            </h4>
            <div className="relative h-36 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <SimpleBarChart data={weeklyData} dataKey="sodium" goal={goals.sodium_mg || 0} color="bg-blue-400" isKo={isKo} />
            </div>
          </div>

          {/* Protein Chart */}
          <div>
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-2">
              <Beef className="text-red-500" size={16} />
              {isKo ? '단백질' : 'Protein'}
            </h4>
            <div className="relative h-36 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <SimpleBarChart data={weeklyData} dataKey="protein" goal={goals.protein_g || 0} color="bg-red-400" isKo={isKo} />
            </div>
          </div>
        </div>
      </div>}

      {/* Insights Section */}
      {!loading && !error && hasRecordedMeals && insights.length > 0 && <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
          <Target className="text-indigo-500" size={20} />
          {isKo ? 'AI 영양 인사이트' : 'AI Nutrition Insights'}
        </h3>

        <div className="space-y-3">
          {insights.map((insight, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg flex items-start gap-3 ${
                insight.type === 'warning'
                  ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
                  : insight.type === 'success'
                    ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                    : 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
              }`}
            >
              {insight.type === 'warning' && <AlertTriangle className="text-yellow-500 flex-shrink-0 mt-0.5" size={20} />}
              {insight.type === 'success' && <CheckCircle2 className="text-green-500 flex-shrink-0 mt-0.5" size={20} />}
              <p className="text-gray-700 dark:text-gray-300">
                {isKo ? insight.message : insight.messageEn}
              </p>
            </div>
          ))}
        </div>
      </div>}

      {/* Recommendations */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 rounded-xl text-white">
        <h3 className="text-xl font-bold mb-4">
          {isKo ? '맞춤 추천' : 'Personalized Recommendations'}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white/10 p-4 rounded-lg">
            <h4 className="font-semibold mb-2 flex items-center gap-2">
              <ArrowRight size={16} />
              {isKo ? '나트륨 섭취 줄이기' : 'Reduce Sodium Intake'}
            </h4>
            <p className="text-sm opacity-90">
              {isKo
                ? '이번 주 나트륨 섭취량이 목표치를 초과했습니다. 가공식품 대신 신선한 재료를 사용해 보세요.'
                : 'Your sodium intake exceeded the target this week. Try using fresh ingredients instead of processed foods.'}
            </p>
          </div>
          <div className="bg-white/10 p-4 rounded-lg">
            <h4 className="font-semibold mb-2 flex items-center gap-2">
              <ArrowRight size={16} />
              {isKo ? '단백질 균형 맞추기' : 'Balance Protein Intake'}
            </h4>
            <p className="text-sm opacity-90">
              {isKo
                ? '단백질 섭취가 약간 불규칙합니다. 매끼 일정한 양의 양질의 단백질을 섭취하세요.'
                : 'Your protein intake is slightly irregular. Try to consume consistent amounts of quality protein with each meal.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NutritionAnalysisContent;
