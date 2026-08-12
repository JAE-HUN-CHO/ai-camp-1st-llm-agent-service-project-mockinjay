import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Star, ChevronRight } from 'lucide-react';
import { MobileHeader } from '../../components/layout/MobileHeader';
import { ImageWithFallback } from '../../components/ui/image-with-fallback';
import { storage } from '../../utils/storage';
import api from '../../services/api';
import { createNewsBookmark, deleteNewsBookmark, getNewsBookmarks, type NewsBookmark } from '../../services/bookmarkApi';

interface NewsArticle {
  id: string;
  title: string;
  source: string;
  pubDate: string;
  time: string;
  description?: string | null;
  content?: string | null;
  image?: string | null;
  link: string;
  language?: string;
}

export default function NewsDetailPage() {
  const navigate = useNavigate();
  const { id: articleId } = useParams<{ id: string }>();
  const userId = storage.get<{ id: string }>('careguide_user')?.id;
  const [article, setArticle] = useState<NewsArticle | null>(null);
  const [related, setRelated] = useState<NewsArticle[]>([]);
  const [bookmark, setBookmark] = useState<NewsBookmark | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!articleId) {
      setError('뉴스 식별자가 없습니다.');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.get<NewsArticle>(`/api/news/detail/${encodeURIComponent(articleId)}`)
      .then(({ data }) => {
        if (cancelled) return;
        setArticle(data);
        return api.post<{ articles: NewsArticle[] }>('/api/news/list', {
          query: data.title,
          language: data.language || 'en',
          page: 1,
          page_size: 6,
          source: 'auto',
        });
      })
      .then((response) => {
        if (!cancelled && response) setRelated(response.data.articles.filter((item) => item.id !== articleId));
      })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : '뉴스를 불러오지 못했습니다.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [articleId]);

  useEffect(() => {
    if (!userId || !articleId) return;
    getNewsBookmarks(userId)
      .then((items) => setBookmark(items.find((item) => item.itemId === articleId) || null))
      .catch((err) => console.error('뉴스 북마크 상태를 불러오지 못했습니다.', err));
  }, [articleId, userId]);

  const toggleBookmark = async () => {
    if (!article || !articleId) return;
    if (!userId) { setError('뉴스를 저장하려면 로그인해 주세요.'); return; }
    try {
      if (bookmark) {
        await deleteNewsBookmark(bookmark.id);
        setBookmark(null);
      } else {
        setBookmark(await createNewsBookmark({
          userId,
          articleId,
          title: article.title,
          description: article.description || undefined,
          content: article.content || undefined,
          source: article.source,
          pubDate: article.pubDate,
          image: article.image || undefined,
          link: article.link,
          language: article.language,
        }));
      }
    } catch (err) { setError(err instanceof Error ? err.message : '뉴스 북마크를 저장하지 못했습니다.'); }
  };

  if (loading) return <div className="flex flex-col h-screen bg-white"><MobileHeader title="새소식" /><p className="p-8 text-center text-gray-500">뉴스를 불러오는 중...</p></div>;
  if (error || !article) return <div className="flex flex-col h-screen bg-white"><MobileHeader title="새소식" /><div className="p-8 text-center text-red-600">{error || '뉴스를 찾을 수 없습니다.'}</div></div>;

  return <div className="flex flex-col h-screen bg-white">
    <MobileHeader title="새소식" rightAction={<button onClick={toggleBookmark} className="p-1" aria-label={bookmark ? '북마크 제거' : '북마크 추가'}><Star size={24} color={bookmark ? '#FFD700' : '#E0E0E0'} fill={bookmark ? '#FFD700' : 'none'} /></button>} />
    <div className="flex-1 overflow-y-auto p-5 pb-10 no-scrollbar"><div className="max-w-4xl mx-auto">
      <div className="w-full aspect-video bg-gray-100 rounded-xl mb-6 overflow-hidden"><ImageWithFallback src={article.image || ''} alt={article.title} className="w-full h-full object-cover" /></div>
      <h1 className="text-[18px] lg:text-2xl font-bold text-[#1F2937] leading-[1.4] mb-3">{article.title}</h1>
      <div className="text-xs lg:text-sm text-[#999999] mb-6 flex items-center gap-2"><span>{article.source}</span><span>-</span><span>{article.pubDate || article.time}</span></div>
      <div className="h-[1px] bg-[#E0E0E0] w-full mb-8" />
      <div className="text-base text-[#1F2937] leading-[1.6] whitespace-pre-line mb-10">{article.content || article.description || '본문이 제공되지 않은 기사입니다.'}</div>
      <a href={article.link} target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 w-full h-[52px] rounded-xl border border-[#E0E0E0] bg-white text-[#1F2937] font-medium mb-12 hover:bg-gray-50"><span>원문 보기</span><ChevronRight size={20} /></a>
      {related.length > 0 && <div><h2 className="text-[18px] font-bold text-[#1F2937] mb-4">관련 뉴스</h2><div className="grid grid-cols-1 md:grid-cols-3 gap-4">{related.map((item) => <button key={item.id} onClick={() => navigate(`/news/detail/${item.id}`)} className="flex md:flex-col gap-3 p-3 rounded-xl border border-[#E0E0E0] bg-white text-left hover:bg-gray-50"><div className="w-[80px] h-[80px] md:w-full md:h-[140px] bg-gray-100 rounded-lg overflow-hidden"><ImageWithFallback src={item.image || ''} alt="" className="w-full h-full object-cover" /></div><div><h3 className="text-[14px] font-bold text-[#1F2937] line-clamp-2">{item.title}</h3><span className="text-xs text-[#999999]">{item.time}</span></div></button>)}</div></div>}
    </div></div>
  </div>;
}
