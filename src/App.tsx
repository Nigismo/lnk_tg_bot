import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';

// ВСТАВЬ СЮДА СВОЮ ССЫЛКУ СБП ИЛИ НОМЕР ТЕЛЕФОНА
const PAYMENT_DATA = "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79270920073&bankCode=100000000111"; 

export default function App() {
  const [showPayment, setShowPayment] = useState(false);
  const [paymentSent, setPaymentSent] = useState(false);

  const handleConfirmPayment = () => {
    setPaymentSent(true);
    // Здесь можно добавить вызов tg.sendData() или API запроса к боту
    // чтобы уведомить админа о том, что юзер нажал "Я оплатил"
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-6 font-sans">
      
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
          Premium VPN
        </h1>
        <p className="text-gray-400 mt-2 font-medium">Твой персональный узел связи</p>
      </div>

      {!showPayment ? (
        <div className="bg-gray-800 p-8 rounded-[2rem] shadow-2xl w-full max-w-sm border border-gray-700/50 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
          
          <div className="flex items-baseline justify-center mb-6 mt-2">
            <span className="text-5xl font-extrabold text-white">150₽</span>
            <span className="text-xl text-gray-500 ml-2 font-medium">/ мес</span>
          </div>
          
          <ul className="space-y-4 mb-8 text-gray-300 font-medium">
            <li className="flex items-center gap-3"><span className="text-xl">🚀</span> Максимальная скорость</li>
            <li className="flex items-center gap-3"><span className="text-xl">🛡️</span> Обход всех DPI</li>
            <li className="flex items-center gap-3"><span className="text-xl">📱</span> Подключение в 1 клик</li>
          </ul>
          
          <button 
            onClick={() => setShowPayment(true)}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-4 px-6 rounded-2xl shadow-[0_0_20px_rgba(124,58,237,0.3)] transform transition-all active:scale-95"
          >
            Получить доступ
          </button>
        </div>
      ) : (
        <div className="bg-gray-800 p-8 rounded-[2rem] shadow-2xl w-full max-w-sm border border-gray-700/50 flex flex-col items-center animate-in fade-in zoom-in duration-300">
          <h2 className="text-2xl font-bold mb-2">Оплата по QR</h2>
          <p className="text-gray-400 mb-6 text-center text-sm font-medium">
            Отсканируй код в приложении банка
          </p>
          
          {/* Магия динамического QR-кода */}
          <div className="bg-white p-4 rounded-3xl shadow-[0_0_30px_rgba(255,255,255,0.1)] mb-8 border-4 border-transparent bg-clip-padding relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-500 -m-1 rounded-[1.4rem] -z-10"></div>
            <QRCodeSVG 
              value={PAYMENT_DATA} 
              size={200} 
              level={"H"}
              fgColor={"#111827"} // Темно-серый цвет квадратиков для лучшего считывания
              bgColor={"#ffffff"}
            />
          </div>

          {!paymentSent ? (
            <div className="w-full space-y-3">
              <button 
                onClick={handleConfirmPayment}
                className="w-full bg-green-500 hover:bg-green-400 text-white font-bold py-4 px-6 rounded-2xl shadow-lg transform transition-all active:scale-95"
              >
                ✅ Я оплатил
              </button>
              <button 
                onClick={() => setShowPayment(false)}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-2xl transition-colors"
              >
                Отмена
              </button>
            </div>
          ) : (
             <div className="w-full text-center py-4 bg-gray-900/50 rounded-2xl border border-green-500/30">
               <p className="text-green-400 font-bold mb-1">⏳ Проверяем платеж...</p>
               <p className="text-gray-400 text-xs">Доступ будет выдан в боте</p>
             </div>
          )}
        </div>
      )}
    </div>
  );
}
