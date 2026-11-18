import React, { useEffect } from 'react';
import { useFinsightQuery } from '../lib/hooks/use-query';
import { SidebarSkeleton } from './SidebarSkeleton';
import { bridge } from '../lib/bridge/client';

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
      <div className="p-4">
        <p className="text-red-500 mb-2">Lỗi tải dữ liệu</p>
        <button 
          className="min-h-[48px] min-w-[48px] bg-indigo-500 text-white px-4 py-2 rounded"
          onClick={() => refetch()}
        >
          Thử lại
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-4">
        <p className="text-gray-500 mb-2">Chưa có dữ liệu</p>
        <button 
          className="min-h-[48px] min-w-[48px] bg-indigo-500 text-white px-4 py-2 rounded"
          onClick={() => refetch()}
        >
          Chạy truy vấn
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <p className="mb-4">{data.data}</p>
      <button 
        className="min-h-[48px] min-w-[48px] bg-emerald-500 text-white px-4 py-2 rounded"
        onClick={() => handleCitationClick(data.id)}
      >
        Xem nguồn (ID: {data.id})
      </button>
    </div>
  );
};
