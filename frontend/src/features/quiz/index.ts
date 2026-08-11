/** Quiz feature boundary for quiz sessions and point-awarding completion. */
export { default as QuizPage } from './QuizPage';
export { default as QuizListPage } from './QuizListPage';
export { default as QuizCompletionPage } from './QuizCompletionPage';

export const QUIZ_ROUTES = ['/quiz', '/quiz/play', '/quiz/completion'] as const;

export type QuizRoute = (typeof QUIZ_ROUTES)[number];
