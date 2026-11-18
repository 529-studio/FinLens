import React, { useEffect } from 'react';
import { useFinsightQuery } from '../lib/hooks/use-query';
import { SidebarSkeleton } from './SidebarSkeleton';
import { bridge } from '../lib/bridge/client';
import { 
  RefreshCw, 
  Search, 
  ExternalLink, 
  AlertCircle, 
  CheckCircle,
  FileText
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { data, isLoading, error, refetch } = useFinsightQuery('test-query');

  useEffect(() => {
    bridge.connect();
  }, []);

  const handleCitationClick = (citationId: string) => {
    bridge.sendCitation(citationId);
  };

  if (isLoading) {
    return <SidebarSkeleton />;
  }

  if (error) {
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center text-red-600 gap-2">
          <AlertCircle className="w-5 h-5" />
          <p className="font-semibold text-sm">Lỗi tải dữ liệu</p>
        </div>
        <button 
          className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg font-medium transition"
          onClick={() => refetch()}
        >
          <RefreshCw className="w-4 h-4" />
          Thử lại
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center text-slate-500 gap-2">
          <FileText className="w-5 h-5" />
          <p className="font-medium text-sm">Chưa có dữ liệu</p>
        </div>
        <button 
          className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium transition"
          onClick={() => refetch()}
        >
          <Search className="w-4 h-4" />
          Chạy truy vấn
        </button>
      </div>
    );
  }

  const confidenceScore = data.confidence; 

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-900">Kết quả phân tích</h2>
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
          confidenceScore > 0.9 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
        }`}>
          <CheckCircle className="w-3 h-3" />
          {Math.round(confidenceScore * 100)}% Tự tin
        </div>
      </div>
      
      <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-sm text-slate-700 leading-relaxed">
        {data.data}
      </div>

      <button 
        className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-lg font-medium shadow-sm transition"
        onClick={() => handleCitationClick(data.id)}
      >
        <ExternalLink className="w-4 h-4" />
        Xem nguồn (ID: {data.id})
      </button>
    </div>
  );
};
