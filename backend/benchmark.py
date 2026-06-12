from database import SessionLocal
import models
import matplotlib.pyplot as plt
import json

def run_real_analytics():
    print("Підключення до бази даних та збір реальної статистики...")
    db = SessionLocal()
    
    try:
        submissions = db.query(models.Submission).order_by(models.Submission.created_at.asc()).all()
        
        if not submissions:
            print("База даних порожня. Будь ласка, проженіть кілька кодів через веб-інтерфейс.")
            return

        llm_times = []
        cache_times = []
        ast_times = []
        
        hybrid_cumulative_hours = []
        pure_llm_cumulative_hours = []
        current_hybrid_time = 0
        current_pure_time = 0

        for sub in submissions:
            if sub.execution_time is None:
                continue

            exec_time = sub.execution_time
            feedback = sub.teacher_feedback or ""
            
            is_cache = "[Кеш]" in feedback or "Отримано з кешу" in feedback
            
            try:
                analysis = json.loads(sub.feedback_json) if sub.feedback_json else {}
                score = analysis.get("score")
            except:
                score = None

            is_ast = score in [0, 40] and not is_cache

            if is_cache:
                cache_times.append(exec_time)
                source = "CACHE"
            elif is_ast:
                ast_times.append(exec_time)
                source = "AST"
            else:
                llm_times.append(exec_time)
                source = "LLM"

            current_hybrid_time += exec_time
            hybrid_cumulative_hours.append(current_hybrid_time / 3600)

        avg_llm_time = sum(llm_times) / len(llm_times) if llm_times else 10.0
        
        for _ in submissions:
            current_pure_time += avg_llm_time
            pure_llm_cumulative_hours.append(current_pure_time / 3600)

        total_subs = len(submissions)
        print("\n" + "="*55)
        print("РЕАЛЬНА СТАТИСТИКА ПРОДУКТИВНОСТІ (На основі БД)")
        print("="*55)
        print(f"Всього оброблено робіт: {total_subs}")
        print(f"  - Оброблено Gemini (LLM): {len(llm_times)} (Сер. час: {avg_llm_time:.2f} с)")
        print(f"  - Взято з L1/L2 Кешу:     {len(cache_times)} (Сер. час: {sum(cache_times)/len(cache_times) if cache_times else 0:.2f} с)")
        print(f"  - Відхилено локально AST: {len(ast_times)} (Сер. час: {sum(ast_times)/len(ast_times) if ast_times else 0:.2f} с)")
        print("-" * 55)
        print(f"Час звичайного підходу (Pure LLM): {current_pure_time:.2f} с ➔ {(current_pure_time/3600):.2f} годин")
        print(f"РЕАЛЬНИЙ час гібридної системи:        {current_hybrid_time:.2f} с ➔ {(current_hybrid_time/3600):.2f} годин")
        
        saved_sec = current_pure_time - current_hybrid_time
        saved_hours = saved_sec / 3600
        percent_saved = (1 - current_hybrid_time/current_pure_time)*100
        print(f"ЗЕКОНОМЛЕНО ЧАСУ:                  {saved_sec:.2f} с ➔ {saved_hours:.2f} годин ({percent_saved:.1f}%)")
        print("="*55 + "\n")

        plot_real_data(pure_llm_cumulative_hours, hybrid_cumulative_hours, total_subs)

    finally:
        db.close()

def plot_real_data(pure_llm_hours, hybrid_hours, total_subs):
    plt.figure(figsize=(10, 6))
    
    plt.plot(range(1, total_subs + 1), pure_llm_hours, label='Стандартний підхід (Кожен запит іде до ШІ)', color='#ef4444', linewidth=3)
    plt.plot(range(1, total_subs + 1), hybrid_hours, label='Гібридна Система (Реальні дані)', color='#10b981', linewidth=3)
    
    plt.fill_between(range(1, total_subs + 1), hybrid_hours, pure_llm_hours, color='#10b981', alpha=0.1, label='Фізично зекономлений час')

    plt.title('Експериментальне підтвердження ефективності архітектури', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Кількість перевірених студентських робіт', fontsize=12)
    plt.ylabel('Загальний витрачений час (год)', fontsize=12, fontweight='bold') 
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(fontsize=11)

    plt.savefig('real_benchmark_result_hours.png', dpi=300, bbox_inches='tight')
    print("Графік успішно згенеровано у 'real_benchmark_result_hours.png'")
    plt.show()

if __name__ == "__main__":
    run_real_analytics()