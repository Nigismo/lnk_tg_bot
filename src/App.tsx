import React, { useState } from 'react';
import { PAYMENT_QR_BASE64 } from './constants';

export default function App() {
  // State для переключения между экраном тарифа и экраном QR-кода
  const [showPayment, setShowPayment] = useState(false);

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-6 font-sans">
      
      {/* Заголовок */}
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
          Premium VPN
        </h1>
        <p className="text-gray-400 mt-2 font-medium">Свободный интернет без границ</p>
      </div>

      {!showPayment ? (
        /* ЭКРАН ТАРИФА */
        <div className="bg-gray-800 p-8 rounded-[2rem] shadow-2xl w-full max-w-sm border border-gray-700/50 relative overflow-hidden">
          {/* Декоративный блик */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
          
          <div className="flex items-baseline justify-center mb-6 mt-2">
            <span className="text-5xl font-extrabold text-white">150₽</span>
            <span className="text-xl text-gray-500 ml-2 font-medium">/ мес</span>
          </div>
          
          <ul className="space-y-4 mb-8 text-gray-300 font-medium">
            <li className="flex items-center gap-3">
              <span className="text-xl">🚀</span> Обход блокировок и DPI
            </li>
            <li className="flex items-center gap-3">
              <span className="text-xl">♾️</span> Безлимитный трафик
            </li>
            <li className="flex items-center gap-3">
              <span className="text-xl">🛡️</span> Без логов и рекламы
            </li>
          </ul>
          
          <button 
            onClick={() => setShowPayment(true)}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-4 px-6 rounded-2xl shadow-[0_0_20px_rgba(124,58,237,0.3)] transform transition-all active:scale-95"
          >
            Оплатить доступ
          </button>
        </div>
      ) : (
        /* ЭКРАН ОПЛАТЫ (QR) */
        <div className="bg-gray-800 p-8 rounded-[2rem] shadow-2xl w-full max-w-sm border border-gray-700/50 flex flex-col items-center animate-in fade-in zoom-in duration-300">
          <h2 className="text-2xl font-bold mb-2">Оплата по QR</h2>
          <p className="text-gray-400 mb-6 text-center text-sm font-medium">
            Отсканируй этот код в камере или приложении любого банка
          </p>
          
          {/* Контейнер для QR-кода (белый фон нужен, чтобы камеры банков легко его читали) */}
          <div className="bg-white p-4 rounded-3xl shadow-inner mb-8 border-4 border-gray-700">
            <img 
              src={PAYMENT_QR_BASE64} 
              alt="QR код для оплаты" 
              className="w-56 h-56 object-contain"
              referrerPolicy="no-referrer"
            />
          </div>

          <button 
            onClick={() => setShowPayment(false)}
            className="w-full bg-gray-700/50 hover:bg-gray-700 text-gray-300 font-bold py-3 px-6 rounded-2xl transition-colors"
          >
            ← Назад
          </button>
        </div>
      )}
    </div>
  );
}
