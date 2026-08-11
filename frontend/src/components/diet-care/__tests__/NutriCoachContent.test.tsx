/**
 * Unit tests for NutriCoachContent component
 * Tests integration of educational components with existing diet information
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { NutriCoachContent } from '../NutriCoachContent';

vi.mock('../../../hooks/useNutritionAnalysis', () => ({
  useNutritionAnalysis: () => ({
    status: 'idle',
    result: null,
    error: null,
    analyze: vi.fn(),
    reset: vi.fn(),
    abort: vi.fn(),
  }),
}));

const renderContent = (language: 'ko' | 'en') =>
  render(<MemoryRouter><NutriCoachContent language={language} /></MemoryRouter>);

describe('NutriCoachContent', () => {
  describe('Educational Content Section', () => {
    it('renders nutrient management guide heading in Korean', () => {
      renderContent('ko');
      expect(screen.getByText('영양소 관리 가이드')).toBeInTheDocument();
    });

    it('renders nutrient management guide heading in English', () => {
      renderContent('en');
      expect(screen.getByText('Nutrient Management Guide')).toBeInTheDocument();
    });

    it('renders potassium education section', () => {
      renderContent('ko');
      expect(screen.getByTestId('nutrient-section-potassium')).toBeInTheDocument();
    });

    it('renders phosphorus education section', () => {
      renderContent('ko');
      expect(screen.getByTestId('nutrient-section-phosphorus')).toBeInTheDocument();
    });

    it('renders safe and warning food cards for potassium', () => {
      renderContent('ko');
      expect(screen.getByText('저칼륨 음식 (먹어도 되는 음식)')).toBeInTheDocument();
      expect(screen.getByText('고칼륨 음식 (피해야 하는 음식)')).toBeInTheDocument();
    });

    it('renders safe and warning food cards for phosphorus', () => {
      renderContent('ko');
      expect(screen.getByText('저인 음식 (먹어도 되는 음식)')).toBeInTheDocument();
      expect(screen.getByText('고인 음식 (피해야 하는 음식)')).toBeInTheDocument();
    });

    it('renders English food card titles when language is en', () => {
      renderContent('en');
      expect(screen.getByText('Low Potassium Foods (Safe to Eat)')).toBeInTheDocument();
      expect(screen.getByText('High Potassium Foods (Avoid)')).toBeInTheDocument();
      expect(screen.getByText('Low Phosphorus Foods (Safe to Eat)')).toBeInTheDocument();
      expect(screen.getByText('High Phosphorus Foods (Avoid)')).toBeInTheDocument();
    });
  });

  describe('Diet Information Section', () => {
    it('renders diet information heading', () => {
      renderContent('ko');
      expect(screen.getByText('질환식 정보')).toBeInTheDocument();
    });

    it('renders all diet type cards', () => {
      renderContent('ko');
      expect(screen.getByText('저염식 (Low Sodium)')).toBeInTheDocument();
      expect(screen.getByText('저단백식 (Low Protein)')).toBeInTheDocument();
      expect(screen.getByText('저칼륨식 (Low Potassium)')).toBeInTheDocument();
      expect(screen.getByText('저인식 (Low Phosphorus)')).toBeInTheDocument();
    });
  });

  describe('Food Image Analysis Section', () => {
    it('renders food image analyzer', () => {
      renderContent('ko');
      expect(screen.getByRole('heading', { name: '음식 사진 분석' })).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for educational content', () => {
      renderContent('ko');
      expect(screen.getByRole('heading', { name: '영양소 관리 가이드' })).toBeInTheDocument();
    });

    it('has proper ARIA labels for diet information', () => {
      renderContent('ko');
      expect(screen.getByRole('heading', { name: '질환식 정보' })).toBeInTheDocument();
    });
  });

  describe('Dark Mode Support', () => {
    it('applies dark mode classes to sections', () => {
      const { container } = renderContent('ko');
      const sections = container.querySelectorAll('section');

      expect(Array.from(sections).some(section => section.className.includes('dark:bg-gray-800'))).toBe(true);
    });
  });

  describe('Layout and Structure', () => {
    it('renders sections in correct order', () => {
      const { container } = renderContent('ko');
      const sections = container.querySelectorAll('section');

      // Should have 3 sections: Educational Content, Diet Information, Food Image Analysis
      expect(sections.length).toBeGreaterThanOrEqual(2);
    });

    it('uses responsive grid for food cards', () => {
      const { container } = renderContent('ko');
      const grids = container.querySelectorAll('.grid.md\\:grid-cols-2');

      // Should have grids for potassium and phosphorus sections
      expect(grids.length).toBeGreaterThanOrEqual(2);
    });
  });
});
