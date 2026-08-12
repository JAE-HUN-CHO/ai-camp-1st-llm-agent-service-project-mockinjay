import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Star, ExternalLink } from 'lucide-react';
import { MobileHeader } from '../../components/layout/MobileHeader';
import { useAuth } from '../../contexts/AuthContext';
import { useBookmarks } from '../../hooks/useBookmarks';
import {
  deleteNewsBookmark,
  getNewsBookmarks,
  type NewsBookmark,
} from '../../services/bookmarkApi';

export default function BookmarkPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { bookmarks: paperList, loading: papersLoading, error: papersError } = useBookmarks(user?.id);
  const [activeTab, setActiveTab] = useState<'news' | 'papers'>('news');
  const [newsList, setNewsList] = useState<NewsBookmark[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsError, setNewsError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.id) return;
    let cancelled = false;
    setNewsLoading(true);
    getNewsBookmarks(user.id)
      .then((items) => { if (!cancelled) setNewsList(items); })
      .catch((error) => {
        if (!cancelled) setNewsError(error instanceof Error ? error.message : '뉴스 북마크를 불러오지 못했습니다.');
      })
      .finally(() => { if (!cancelled) setNewsLoading(false); });
    return () => { cancelled = true; };
  }, [user?.id]);

  const removeNews = async (id: string) => {
    if (!window.confirm('즐겨찾기에서 삭제하시겠습니까?')) return;
    try {
      await deleteNewsBookmark(id);
      setNewsList((items) => items.filter((item) => item.id !== id));
    } catch (error) {
      setNewsError(error instanceof Error ? error.message : '뉴스 북마크를 삭제하지 못했습니다.');
    }
  };

  const loading = activeTab === 'news' ? newsLoading : papersLoading;
  const error = activeTab === 'news' ? newsError : papersError;

  return (
    <div className="flex flex-col h-screen bg-white">
      <MobileHeader title="즐겨찾기" />
      <div className="px-5 border-b border-[#E0E0E0] bg-white sticky top-[52px] z-40">
        <div className="flex gap-6">
          {(['news', 'papers'] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)} className={`pb-3 text-base font-medium transition-colors relative ${activeTab === tab ? 'text-[#00C9B7]' : 'text-[#999999]'}`}>
              {tab === 'news' ? '뉴스' : '논문'}
              {activeTab === tab && <div className="absolute bottom-0 left-0 w-full h-[2px] bg-[#00C9B7]" />}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-5 pb-24 lg:pb-10">
        {loading && <p className="py-12 text-center text-gray-500">불러오는 중...</p>}
        {error && <p className="py-12 text-center text-red-600">{error}</p>}
        {!loading && !error && activeTab === 'news' && (
          newsList.length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {newsList.map((bookmark) => {
                const article = bookmark.itemData;
                return <div key={bookmark.id} className="flex gap-4 p-4 rounded-xl border border-[#E0E0E0] bg-white">
                  <button className="w-[80px] h-[80px] bg-gray-100 rounded-lg flex-shrink-0" onClick={() => navigate(`/news/detail/${bookmark.itemId}`)} aria-label={`${article.title} 상세 보기`}>
                    {article.image && <img src={article.image} alt="" className="w-full h-full object-cover rounded-lg" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-2 mb-1">
                      <button className="text-left text-[15px] font-bold text-[#1F2937] leading-[1.4] line-clamp-2 hover:text-[#00C9B7]" onClick={() => navigate(`/news/detail/${bookmark.itemId}`)}>{article.title}</button>
                      <button onClick={() => removeNews(bookmark.id)} className="text-[#FFD700] flex-shrink-0" aria-label="뉴스 북마크 삭제"><Star size={20} fill="#FFD700" /></button>
                    </div>
                    <div className="text-xs text-[#999999] flex gap-2"><span>{article.source}</span><span>-</span><span>{article.pubDate}</span></div>
                  </div>
                </div>;
              })}
            </div>
          ) : <EmptyState label="즐겨찾기한 뉴스가 없습니다." />
        )}
        {!loading && !error && activeTab === 'papers' && (
          paperList.length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {paperList.map((paper) => <div key={paper.id} className="p-5 rounded-xl border border-[#E0E0E0] bg-white h-full flex flex-col">
                <div className="flex justify-between items-start gap-2 mb-2"><h3 className="text-[16px] font-bold text-[#1F2937] leading-[1.4]">{paper.title || paper.paperData?.title}</h3><span className="text-[#FFD700]"><Star size={20} fill="#FFD700" /></span></div>
                <div className="text-sm text-[#666666] mb-1">{(paper.authors || paper.paperData?.authors || []).join(', ')}</div>
                <div className="flex items-center gap-3 text-xs text-[#999999] mb-4"><span>{paper.pubDate || paper.paperData?.pub_date}</span><span>PMID: {paper.paperId}</span></div>
                <a href={paper.url || paper.paperData?.url} target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 w-full h-[44px] rounded-lg border border-[#E0E0E0] bg-white text-[#1F2937] font-medium hover:bg-gray-50 mt-auto"><span>논문 보기</span><ExternalLink size={16} /></a>
              </div>)}
            </div>
          ) : <EmptyState label="즐겨찾기한 논문이 없습니다." />
        )}
      </div>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="flex flex-col items-center justify-center py-20 text-[#999999]"><Star size={40} className="mb-3 opacity-30" /><p>{label}</p></div>;
}
