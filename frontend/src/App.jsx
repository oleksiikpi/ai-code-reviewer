import React, { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import axios from 'axios';
import { Code2, Cpu, MessageSquare, AlertTriangle, CheckCircle, History, User, ChevronDown, Sparkles, Activity } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

function App() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [history, setHistory] = useState([]);
  const feedbackContainerRef = useRef(null);
  const [studentName, setStudentName] = useState('');
  const [expandedHistoryId, setExpandedHistoryId] = useState(null);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/reviews/history`);
      setHistory(response.data);
    } catch (error) {
      console.error("Помилка завантаження історії:", error);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleVerifyCode = async () => {
    setLoading(true);
    setFeedback(null);

    if (feedbackContainerRef.current) {
      feedbackContainerRef.current.scrollTop = 0;
    }

    try {
      const response = await axios.post(`${API_URL}/reviews/analyze`, {
        code: code,
        language: 'python',
        student_name: studentName
      });
      setFeedback(response.data);
      fetchHistory();
    } catch (error) {
      console.error("Помилка верифікації коду:", error);
      if (error.response && error.response.status === 429) {
        setFeedback({
          status: "error",
          message: error.response.data.detail
        });
      } else {
        setFeedback({
          status: "error",
          message: "Не вдалося зв'язатися з сервером верифікації. Перевірте статус контейнера бекенду."
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const cleanMarkdown = (text) => {
    if (!text) return 'Результат аналізу відсутній.';
    return text.replace(/[*#]/g, '').trim();
  };

  const toggleHistoryItem = (id) => {
    setExpandedHistoryId(prevId => (prevId === id ? null : id));
  };

  const renderIssuesDetail = (issues) => {
    if (!issues || issues.length === 0) return null;
    
    return (
      <div className="space-y-3 mt-4">
        <h5 className="text-xs font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1">
          <Sparkles className="h-3.5 w-3.5" /> Деталізація виявлених дефектів:
        </h5>
        {issues.map((issue, index) => {
          let badgeStyles = "bg-blue-500/10 text-blue-400 border-blue-500/30";
          let leftBorder = "border-l-4 border-l-blue-500";
          let badgeLabel = "Порада";

          if (issue.severity === 'error') {
            badgeStyles = "bg-rose-500/10 text-rose-400 border-rose-500/30";
            leftBorder = "border-l-4 border-l-rose-500";
            badgeLabel = "Критична помилка";
          } else if (issue.severity === 'warning') {
            badgeStyles = "bg-amber-500/10 text-amber-400 border-amber-500/30";
            leftBorder = "border-l-4 border-l-amber-500";
            badgeLabel = "Зауваження";
          }

          const lineText = issue.line_start 
            ? (issue.line_end && issue.line_end !== issue.line_start ? `Рядки ${issue.line_start}-${issue.line_end}` : `Рядок ${issue.line_start}`)
            : "Загальне зауваження";

          return (
            <details key={index} className={`group bg-slate-900/60 rounded-lg border border-slate-700/80 overflow-hidden transition-all duration-150 open:bg-slate-900 ${leftBorder}`}>
              <summary className="flex items-center justify-between p-3 cursor-pointer select-none focus:outline-none list-none">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${badgeStyles} shrink-0`}>
                    {badgeLabel}
                  </span>
                  <span className="text-xs text-slate-500 font-mono shrink-0">({lineText})</span>
                  <span className="text-sm font-semibold text-slate-200 truncate">{issue.title}</span>
                </div>
                <ChevronDown className="h-4 w-4 text-slate-400 transition-transform duration-200 group-open:rotate-180 shrink-0 ml-2" />
              </summary>
              <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 text-sm text-slate-300 space-y-2.5 font-sans animate-fadeIn">
                <p className="leading-relaxed"><strong className="text-slate-400 font-medium">Опис проблеми:</strong> {issue.explanation}</p>
                <p className="leading-relaxed"><strong className="text-slate-400 font-medium">Як виправити:</strong> {issue.recommendation}</p>
              </div>
            </details>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <Cpu className="h-8 w-8 text-indigo-400 animate-pulse" />
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Інтелектуальна веб-система автоматизованої перевірки коду</h1>
            <p className="text-xs text-slate-400">Модуль гібридного аналізу: AST-Детермінізм + Семантичне ШІ-Ядро</p>
          </div>
        </div>
        <div className="flex items-center space-x-2 bg-slate-900 px-3 py-1.5 rounded-md border border-slate-700">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
          <span className="text-xs text-emerald-400 font-mono">Backend: Connected</span>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 overflow-hidden">
        <div className="bg-slate-800 rounded-xl border border-slate-700 flex flex-col shadow-2xl overflow-hidden">
          <div className="bg-slate-850 px-4 py-3 border-b border-slate-700 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Code2 className="h-5 w-5 text-indigo-400" />
                <span className="text-sm font-semibold text-slate-200">Редактор коду</span>
              </div>

              <div className="flex items-center space-x-2 bg-slate-900 px-3 py-1 rounded-md border border-slate-600 focus-within:border-indigo-500 transition-colors">
                <User className="h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="bg-transparent text-sm text-slate-200 focus:outline-none w-48 placeholder-slate-500"
                  placeholder="Введіть ім'я та прізвище..."
                  title="Ідентифікатор поточного профілю"
                />
              </div>
            </div>

            <button
              onClick={handleVerifyCode}
              disabled={loading || !code.trim() || !studentName.trim()}
              className={`px-5 py-2 rounded-lg font-medium text-sm transition-all duration-200 shadow-md ${
                loading || !code.trim() || !studentName.trim()
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white hover:shadow-indigo-500/20 active:scale-95'
              }`}
            >
              {loading ? 'Аналіз структури...' : 'Відправити на перевірку'}
            </button>
          </div>

          <div className="relative flex-1 min-h-[450px]">
            {!code && (
              <div className="absolute top-[2px] left-[64px] text-slate-500 font-mono text-sm pointer-events-none z-20">
                Напишіть свій Python код тут...
              </div>
            )}
            <div className="absolute inset-0">
              <Editor
                height="100%"
                defaultLanguage="python"
                theme="vs-dark"
                value={code}
                onChange={(value) => setCode(value || '')}
                options={{
                  fontSize: 14,
                  minimap: { enabled: false },
                  automaticLayout: true,
                  scrollbar: { vertical: 'visible', horizontal: 'visible' }
                }}
              />
            </div>
          </div>
        </div>

        <div className="flex flex-col space-y-6">
          <div
            ref={feedbackContainerRef}
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 flex flex-col shadow-2xl flex-1 overflow-y-auto"
          >
            <div className="flex items-center space-x-2 border-b border-slate-700 pb-3 mb-4">
              <MessageSquare className="h-5 w-5 text-indigo-400" />
              <h2 className="text-lg font-bold text-slate-200">Віртуальний Ментор</h2>
            </div>

            {!feedback && !loading && (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500">
                <Cpu className="h-12 w-12 mb-3 stroke-1" />
                <p className="text-sm">Напишіть алгоритм ліворуч та відправте на рев'ю.</p>
                <p className="text-xs mt-1 text-slate-600">Система виконає AST-парсинг та семантичний розбір без прямої видачі готового коду.</p>
              </div>
            )}

            {loading && (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                <p className="text-sm text-slate-300 font-medium">Конвеєр верифікації запущено...</p>
                <p className="text-xs text-slate-500 mt-1">Крок 1: Побудова AST дерева | Крок 2: Пошук патернів | Крок 3: Забезпечення AI JSON</p>
              </div>
            )}

            {feedback && (
              <div className="space-y-4 animate-fadeIn">
                {(() => {
                  let analysisData = feedback.feedback_json;
                  if (typeof analysisData === 'string') {
                    try { 
                      analysisData = JSON.parse(analysisData); 
                    } catch (e) {
                      console.error("Помилка парсингу JSON від ШІ:", e);
                    }
                  }

                  const score = analysisData?.score;
                  const isError = feedback.status === 'error' || score === 0;
                  const isWarning = score > 0 && score < 80;

                  let bgColor = 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200';
                  let Icon = CheckCircle;
                  let iconColor = 'text-emerald-400';
                  let summaryTitle = analysisData?.summary || 'Дефект не виявлено';

                  if (isError) {
                    bgColor = 'bg-rose-950/40 border-rose-800/60 text-rose-200';
                    Icon = AlertTriangle;
                    iconColor = 'text-rose-400';
                    summaryTitle = feedback.status === 'error' ? 'Системний збій' : (analysisData?.summary || 'Критична помилка');
                  } else if (isWarning) {
                    bgColor = 'bg-amber-950/40 border-amber-800/60 text-amber-200';
                    Icon = AlertTriangle;
                    iconColor = 'text-amber-400';
                    summaryTitle = analysisData?.summary || 'Виявлено зауваження';
                  }

                  return (
                    <>
                      <div className={`p-4 rounded-lg border flex items-center justify-between space-x-3 ${bgColor}`}>
                        <div className="flex items-start space-x-3">
                          <Icon className={`h-6 w-6 shrink-0 mt-0.5 ${iconColor}`} />
                          <div>
                            <h4 className="font-bold text-sm">{summaryTitle}</h4>
                            <span className="text-xs opacity-75 font-mono block mt-1">
                              Час обробки: {(feedback.execution_time !== undefined && feedback.execution_time !== null) ? `${feedback.execution_time} с` : 'Отримано з кешу'}
                            </span>
                          </div>
                        </div>
                        {score !== undefined && score !== null && (
                          <div className="flex flex-col items-end shrink-0 pl-4 border-l border-current border-opacity-20">
                            <span className="text-[10px] uppercase tracking-widest opacity-70 mb-0.5">Оцінка</span>
                            <span className="text-2xl font-black font-mono leading-none">{score}<span className="text-sm opacity-50 font-sans font-normal">/100</span></span>
                          </div>
                        )}
                      </div>

                      <div className="bg-slate-900 rounded-lg p-4 border border-slate-700/60 text-sm text-slate-300">
                        <div className="whitespace-pre-wrap leading-relaxed">
                          {cleanMarkdown(feedback.teacher_feedback)}
                        </div>
                        {renderIssuesDetail(analysisData?.issues)}
                      </div>

                      {analysisData?.improvements && analysisData.improvements.length > 0 && (
                        <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700/50 space-y-2">
                          <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Рекомендації щодо архітектури:</h5>
                          <ul className="list-disc list-inside text-sm text-slate-300 space-y-1 pl-1">
                            {analysisData.improvements.map((imp, idx) => <li key={idx}>{imp}</li>)}
                          </ul>
                        </div>
                      )}

                      {analysisData?.complexity && (
                        <div className="bg-slate-900/30 p-4 rounded-lg border border-slate-700/50 space-y-2">
                          <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                            <Activity className="h-3.5 w-3.5" /> Обчислювальна складність алгоритму:
                          </h5>
                          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                            <div className="bg-slate-900 p-2 rounded border border-slate-800">
                              <span className="text-slate-500 block mb-0.5">Time Complexity:</span>
                              <span className="text-sky-400 text-sm font-bold">{analysisData.complexity.time || 'N/A'}</span>
                            </div>
                            <div className="bg-slate-900 p-2 rounded border border-slate-800">
                              <span className="text-slate-500 block mb-0.5">Space Complexity:</span>
                              <span className="text-sky-400 text-sm font-bold">{analysisData.complexity.space || 'N/A'}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      </div>

      <footer className="bg-slate-850 border-t border-slate-700 p-6 md:p-8 shadow-2xl mt-auto">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center space-x-2 mb-6">
            <History className="h-6 w-6 text-indigo-400" />
            <h3 className="text-xl font-bold text-slate-200">Журнал перевірок коду</h3>
          </div>
          
          <div className="space-y-3">
            {history.map((item) => (
              <div key={item.id} className="border border-slate-700 rounded-lg overflow-hidden bg-slate-900/50">
                
                <div 
                  className="flex flex-wrap items-center justify-between p-4 cursor-pointer hover:bg-slate-800 transition-colors"
                  onClick={() => toggleHistoryItem(item.id)}
                >
                  <div className="flex items-center gap-3 sm:gap-4 mb-2 sm:mb-0">
                    <span className="font-bold text-indigo-400 text-sm md:text-base">#{item.id}</span>
                    <span className="font-semibold text-emerald-400 text-sm md:text-base">{item.student_name || 'Гість'}</span>
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-400 text-xs uppercase border border-slate-700">
                      {item.language}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <span className="text-slate-400 text-xs md:text-sm font-mono flex items-center gap-1.5">
                      <Activity className="w-4 h-4 text-slate-500" />
                      {item.execution_time ? (item.execution_time < 0.01 ? '< 0.01 с' : `${item.execution_time} с`) : 'Кешовано'}
                    </span>
                    <ChevronDown 
                      className={`w-5 h-5 text-slate-500 transition-transform duration-200 ${expandedHistoryId === item.id ? 'rotate-180' : ''}`} 
                    />
                  </div>
                </div>

                {expandedHistoryId === item.id && (
                  <div className="p-4 md:p-6 border-t border-slate-700 bg-slate-800/30 flex flex-col xl:flex-row gap-6">
                    
                    <div className="flex-1 min-w-0">
                      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Надісланий код</h4>
                      <pre className="p-4 bg-[#1e1e1e] text-slate-300 rounded-md overflow-x-auto font-mono text-sm border border-slate-800 max-h-[500px]">
                        <code>{item.code}</code>
                      </pre>
                    </div>
                    
                    <div className="flex-1 min-w-0 flex flex-col">
                      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Результат аналізу</h4>
                      <div className="p-4 text-slate-300 text-sm leading-relaxed whitespace-pre-wrap bg-slate-900/60 rounded-md border border-slate-700 flex-1 overflow-y-auto max-h-[500px]">
                        {cleanMarkdown(item.teacher_feedback)}
                        
                        {item.feedback_json && renderIssuesDetail(item.feedback_json.issues)}
                      </div>
                    </div>
                    
                  </div>
                )}
              </div>
            ))}

            {history.length === 0 && (
              <div className="p-8 text-center text-slate-500 bg-slate-800/30 rounded-lg border border-slate-700 border-dashed">
                Історія порожня. Дані відображатимуться після першої перевірки коду.
              </div>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;