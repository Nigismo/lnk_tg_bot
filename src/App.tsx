/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        showAlert: (message: string) => void;
        ready: () => void;
      };
    };
  }
}

export const ConnectButton = ({ happLink }: { happLink: string }) => {
  const handleConnect = () => {
    // Пытаемся открыть deep link напрямую
    window.location.href = happLink;
    
    // Fallback: копируем в буфер, если приложение не установлено
    navigator.clipboard.writeText(happLink).then(() => {
      // Вызываем Telegram popup, чтобы сказать:
      // "Если приложение HAPP не открылось, ссылка скопирована в буфер!"
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert("Если приложение HAPP не открылось, ссылка скопирована в буфер!");
      } else {
        alert("Если приложение HAPP не открылось, ссылка скопирована в буфер!");
      }
    }).catch(err => {
      console.error("Ошибка копирования в буфер: ", err);
    });
  };

  return (
    <button 
      onClick={handleConnect}
      className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-2xl shadow-lg transform transition active:scale-95"
    >
      🚀 Подключить в один клик
    </button>
  );
};

export default function App() {
  // В реальном приложении ссылка должна приходить с бэкенда (например, через API)
  const [happLink] = useState("happ://add-profile?url=example");

  // Сообщаем Telegram, что Web App готово к отображению
  React.useEffect(() => {
    if (window.Telegram?.WebApp?.ready) {
      window.Telegram.WebApp.ready();
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-6 font-sans">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-sm border border-slate-100 p-8 mt-10">
        <h1 className="text-2xl font-bold text-slate-900 mb-2 text-center">VPN Подписка</h1>
        <p className="text-slate-500 text-center mb-8">
          Статус: <span className="text-emerald-500 font-semibold">Активна</span>
        </p>
        
        <ConnectButton happLink={happLink} />
        
        <p className="text-xs text-slate-400 text-center mt-6">
          Нажмите на кнопку, чтобы автоматически добавить конфигурацию в приложение HAPP.
        </p>
      </div>
    </div>
  );
}
