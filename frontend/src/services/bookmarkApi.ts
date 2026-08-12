/** Persisted bookmark API. No client-side fallback is used for product data. */
import api from './api';
import type { BookmarkedPaper } from '../types/mypage';
import type { PaperResult } from './trendsApi';

export interface CreateBookmarkRequest {
  userId: string;
  paper: PaperResult;
  tags?: string[];
  notes?: string;
}

export interface UpdateBookmarkRequest {
  tags?: string[];
  notes?: string;
}

export interface BookmarkResponse {
  bookmark: BookmarkedPaper;
  status: string;
}

export interface BookmarksListResponse {
  bookmarks: BookmarkedPaper[];
  total: number;
  status: string;
}

export interface NewsBookmark {
  id: string;
  userId: string;
  itemType: 'news';
  itemId: string;
  itemData: {
    title: string;
    description?: string;
    content?: string;
    source: string;
    pubDate: string;
    image?: string;
    link: string;
    language: string;
  };
  createdAt: string;
  bookmarkedAt: string;
}

export interface NewsBookmarkResponse {
  bookmarks: NewsBookmark[];
  total: number;
  status: string;
}

export interface CreateNewsBookmarkRequest {
  userId: string;
  articleId: string;
  title: string;
  description?: string;
  content?: string;
  source: string;
  pubDate: string;
  image?: string;
  link: string;
  language?: string;
}

export async function createBookmark(request: CreateBookmarkRequest): Promise<BookmarkedPaper> {
  const { data } = await api.post<BookmarkResponse>('/api/bookmarks', {
    user_id: request.userId,
    paper_id: request.paper.pmid,
    title: request.paper.title,
    authors: request.paper.authors || [],
    journal: request.paper.journal || '',
    pub_date: request.paper.pub_date || '',
    abstract: request.paper.abstract || '',
    url: request.paper.url || '',
    tags: request.tags || [],
    notes: request.notes || '',
  });
  return data.bookmark;
}

export async function getBookmarks(userId: string): Promise<BookmarkedPaper[]> {
  const { data } = await api.get<BookmarksListResponse>('/api/bookmarks', {
    params: { user_id: userId },
  });
  return data.bookmarks;
}

export async function isBookmarked(userId: string, paperId: string): Promise<boolean> {
  const bookmarks = await getBookmarks(userId);
  return bookmarks.some((bookmark) => bookmark.paperId === paperId);
}

export async function updateBookmark(
  bookmarkId: string,
  _userId: string,
  updates: UpdateBookmarkRequest
): Promise<BookmarkedPaper> {
  const { data } = await api.patch<BookmarkResponse>(`/api/bookmarks/${bookmarkId}`, updates);
  return data.bookmark;
}

export async function deleteBookmark(bookmarkId: string, _userId: string): Promise<void> {
  await api.delete(`/api/bookmarks/${bookmarkId}`);
}

export async function deleteBookmarkByPaperId(paperId: string, userId: string): Promise<void> {
  const bookmarks = await getBookmarks(userId);
  const bookmark = bookmarks.find((item) => item.paperId === paperId);
  if (bookmark) await deleteBookmark(bookmark.id, userId);
}

export async function getNewsBookmarks(userId: string): Promise<NewsBookmark[]> {
  const { data } = await api.get<NewsBookmarkResponse>('/api/bookmarks/news', {
    params: { user_id: userId },
  });
  return data.bookmarks;
}

export async function createNewsBookmark(request: CreateNewsBookmarkRequest): Promise<NewsBookmark> {
  const { data } = await api.post<{ bookmark: NewsBookmark }>('/api/bookmarks/news', {
    user_id: request.userId,
    article_id: request.articleId,
    title: request.title,
    description: request.description,
    content: request.content,
    source: request.source,
    pub_date: request.pubDate,
    image: request.image,
    link: request.link,
    language: request.language || 'en',
  });
  return data.bookmark;
}

export async function deleteNewsBookmark(bookmarkId: string): Promise<void> {
  await api.delete(`/api/bookmarks/news/${bookmarkId}`);
}
