import { useState, useEffect, useCallback } from 'react';
import { Plus, Loader2 } from 'lucide-react';
import { MobileHeader } from '../../components/layout/MobileHeader';
import api from '../../services/api';
import { toast } from 'sonner';

interface HealthRecord {
  id: string;
  user_id: string;
  date: string;
  hospital: string;
  creatinine: number;
  gfr: number;
  potassium?: number | null;
  phosphorus?: number | null;
  hemoglobin?: number | null;
  albumin?: number | null;
  pth?: number | null;
  hco3?: number | null;
  memo?: string | null;
}

type FormData = {
  date: string;
  hospital: string;
  creatinine: string;
  gfr: string;
  potassium: string;
  phosphorus: string;
  hemoglobin: string;
  albumin: string;
  pth: string;
  hco3: string;
  memo: string;
};

const EMPTY_FORM: FormData = {
  date: '', hospital: '', creatinine: '', gfr: '',
  potassium: '', phosphorus: '', hemoglobin: '', albumin: '',
  pth: '', hco3: '', memo: ''
};

function parseOptional(val: string): number | null {
  const n = parseFloat(val);
  return isNaN(n) ? null : n;
}

export default function HealthRecordsPage() {
  const [records, setRecords] = useState<HealthRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>(EMPTY_FORM);

  const fetchRecords = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<HealthRecord[]>('/api/health-records/');
      setRecords(res.data);
    } catch (err) {
      console.error('[HealthRecords] fetchRecords failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  const handleEdit = (record: HealthRecord) => {
    setFormData({
      date: record.date,
      hospital: record.hospital,
      creatinine: record.creatinine?.toString() ?? '',
      gfr: record.gfr?.toString() ?? '',
      potassium: record.potassium?.toString() ?? '',
      phosphorus: record.phosphorus?.toString() ?? '',
      hemoglobin: record.hemoglobin?.toString() ?? '',
      albumin: record.albumin?.toString() ?? '',
      pth: record.pth?.toString() ?? '',
      hco3: record.hco3?.toString() ?? '',
      memo: record.memo ?? '',
    });
    setEditingId(record.id);
    setIsFormOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/api/health-records/${id}`);
      setRecords(prev => prev.filter(r => r.id !== id));
      toast.success('기록이 삭제되었습니다.');
    } catch (err) {
      console.error('[HealthRecords] handleDelete failed:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const creatinine = parseFloat(formData.creatinine);
    const gfr = parseFloat(formData.gfr);
    if (isNaN(creatinine) || isNaN(gfr)) {
      toast.error('크레아티닌과 사구체여과율은 유효한 숫자여야 합니다.');
      return;
    }

    setSaving(true);

    const payload = {
      date: formData.date,
      hospital: formData.hospital,
      creatinine,
      gfr,
      potassium: parseOptional(formData.potassium),
      phosphorus: parseOptional(formData.phosphorus),
      hemoglobin: parseOptional(formData.hemoglobin),
      albumin: parseOptional(formData.albumin),
      pth: parseOptional(formData.pth),
      hco3: parseOptional(formData.hco3),
      memo: formData.memo || null,
    };

    try {
      if (editingId) {
        await api.put(`/api/health-records/${editingId}`, payload);
        toast.success('기록이 수정되었습니다.');
      } else {
        await api.post('/api/health-records/', payload);
        toast.success('기록이 저장되었습니다.');
      }
      await fetchRecords();
      setIsFormOpen(false);
      setEditingId(null);
      setFormData(EMPTY_FORM);
    } catch (err) {
      console.error('[HealthRecords] handleSubmit failed:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      <MobileHeader title="병원 검진 기록" />

      <div className="flex-1 overflow-y-auto p-5 pb-24 lg:pb-10">
        {!isFormOpen ? (
          <>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-[18px] font-bold text-[#1F2937]">검진 기록</h2>
              <button
                onClick={() => { setEditingId(null); setFormData(EMPTY_FORM); setIsFormOpen(true); }}
                className="flex items-center gap-1 text-[#00C9B7] font-medium"
              >
                <Plus size={20} strokeWidth={2} />
                <span>기록 추가</span>
              </button>
            </div>

            {loading ? (
              <div className="flex justify-center items-center py-20">
                <Loader2 size={32} className="animate-spin text-[#00C9B7]" />
              </div>
            ) : records.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-[#999999] text-base mb-1">아직 기록이 없습니다.</p>
                <p className="text-[#BBBBBB] text-sm">검진 후 수치를 기록해 보세요.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {records.map((record) => (
                  <div key={record.id} className="p-5 rounded-xl border border-[#E0E0E0] bg-white">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-[16px] font-bold text-[#1F2937] mb-1">{record.date}</h3>
                        <p className="text-sm text-[#666666]">{record.hospital}</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(record)}
                          className="text-xs px-2 py-1 border border-[#E0E0E0] rounded text-[#666666]"
                        >
                          수정
                        </button>
                        <button
                          onClick={() => handleDelete(record.id)}
                          className="text-xs px-2 py-1 border border-[#E0E0E0] rounded text-[#EF4444]"
                        >
                          삭제
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-xs text-[#999999] mb-1">크레아티닌</div>
                        <div className="text-[16px] font-bold text-[#1F2937]">{record.creatinine}</div>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-xs text-[#999999] mb-1">eGFR</div>
                        <div className="text-[16px] font-bold text-[#1F2937]">{record.gfr}</div>
                      </div>
                      {record.potassium != null && (
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-xs text-[#999999] mb-1">칼륨</div>
                          <div className="text-[16px] font-bold text-[#1F2937]">{record.potassium}</div>
                        </div>
                      )}
                      {record.hemoglobin != null && (
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-xs text-[#999999] mb-1">헤모글로빈</div>
                          <div className="text-[16px] font-bold text-[#1F2937]">{record.hemoglobin}</div>
                        </div>
                      )}
                    </div>

                    {record.memo && (
                      <div className="text-sm text-[#666666] bg-[#F9FAFB] p-3 rounded-lg">
                        {record.memo}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl mx-auto">
            <h2 className="text-[18px] font-bold text-[#1F2937]">
              {editingId ? '기록 수정' : '새 기록 추가'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#1F2937] mb-2">검진 날짜</label>
                <input
                  type="date"
                  required
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full p-4 rounded-xl border border-[#E0E0E0] outline-none focus:border-[#00C9B7] bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#1F2937] mb-2">병원명</label>
                <input
                  type="text"
                  required
                  placeholder="병원 이름을 입력하세요"
                  value={formData.hospital}
                  onChange={(e) => setFormData({ ...formData, hospital: e.target.value })}
                  className="w-full p-4 rounded-xl border border-[#E0E0E0] outline-none focus:border-[#00C9B7]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: '크레아티닌', key: 'creatinine', required: true },
                  { label: 'eGFR', key: 'gfr', required: true },
                  { label: '칼륨', key: 'potassium', required: false },
                  { label: '인', key: 'phosphorus', required: false },
                  { label: '헤모글로빈', key: 'hemoglobin', required: false },
                  { label: '알부민', key: 'albumin', required: false },
                  { label: 'PTH', key: 'pth', required: false },
                  { label: 'HCO3', key: 'hco3', required: false },
                ].map(({ label, key, required }) => (
                  <div key={key}>
                    <label className="block text-sm font-medium text-[#1F2937] mb-2">
                      {label}{!required && <span className="text-[#AAAAAA] text-xs ml-1">(선택)</span>}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      required={required}
                      value={formData[key as keyof FormData]}
                      onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                      className="w-full p-4 rounded-xl border border-[#E0E0E0] outline-none focus:border-[#00C9B7]"
                    />
                  </div>
                ))}
              </div>

              <div>
                <label className="block text-sm font-medium text-[#1F2937] mb-2">메모</label>
                <textarea
                  rows={3}
                  placeholder="특이사항을 입력하세요"
                  value={formData.memo}
                  onChange={(e) => setFormData({ ...formData, memo: e.target.value })}
                  className="w-full p-4 rounded-xl border border-[#E0E0E0] outline-none focus:border-[#00C9B7] resize-none"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => setIsFormOpen(false)}
                className="flex-1 h-[52px] rounded-xl border border-[#E0E0E0] bg-white text-[#666666] font-medium"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex-1 h-[52px] rounded-xl bg-[#00C9B7] text-white font-medium hover:bg-[#00B3A3] disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {saving && <Loader2 size={16} className="animate-spin" />}
                저장하기
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
