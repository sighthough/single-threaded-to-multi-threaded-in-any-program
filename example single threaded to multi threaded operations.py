import concurrent.futures
import time

class Task:
    def __init__(self, id, priority, dependencies, operation):
        self.id = id                  # e.g., 'A', 'B', 'C'
        self.priority = priority      # Strict order of finalization (1, 2, 3...)
        self.dependencies = dependencies  # List of task IDs this needs
        self.operation = operation    # The actual math/work function
        self.started = False
        self.completed = False
        self.result = None

class OutOfOrderEngine:
    def __init__(self):
        self.tasks = {}
        self.results_registry = {}  # Global state where finalized data lands

    def add_task(self, task):
        self.tasks[task.id] = task

    def run_pipeline(self):
        # We use a ThreadPoolExecutor to simulate multiple CPU cores running in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            
            print("--- PHASE 1: ASYNCHRONOUS ISSUE QUEUE (BACKGROUND) ---")
            futures_map = {}
            
            # Keep looping until all tasks have at least been submitted to a core
            while any(not t.started for t in self.tasks.values()):
                for task in self.tasks.values():
                    if task.started:
                        continue
                    
                    # CHECK DEPENDENCIES: Can this task run right now?
                    deps_met = all(self.tasks[d].completed for d in task.dependencies)
                    
                    if deps_met:
                        print(f"[Issue Queue] Starting Task {task.id} (Priority {task.priority}) on a background core.")
                        task.started = True
                        # Dispatch the job to the thread pool
                        futures_map[task.id] = executor.submit(self._execute_worker, task)
                    else:
                        # THE BYPASS: Task is stalled, leave it in the holding pen and move to the next!
                        print(f"[Issue Queue] Task {task.id} is STALLED waiting for {task.dependencies}. Bypassing...")
                
                # Small pause to allow background threads to progress before checking the queue again
                time.sleep(0.1)

            # Wait for all background threads to wrap up their calculations
            concurrent.futures.wait(futures_map.values())

            print("\n--- PHASE 2: REORDER BUFFER / COMMIT STAGE (FOREGROUND) ---")
            # Sort tasks strictly by their original sequential priority (1, 2, 3...)
            sorted_by_priority = sorted(self.tasks.values(), key=lambda t: task.priority)
            
            for task in sorted_by_priority:
                # The main thread grabs the pre-calculated result from the buffer
                self.results_registry[task.id] = task.result
                print(f"[Reorder Buffer] Committing Task {task.id} (Priority {task.priority}) -> Result: {task.result}")

        print("\nPipeline Complete. Final Single-Threaded State:", self.results_registry)

    def _execute_worker(self, task):
        """The work wrapper executed by background CPU cores."""
        # Gather inputs from previously completed tasks
        inputs = [self.tasks[d].result for d in task.dependencies]
        
        # Run the actual operation
        task.result = task.operation(*inputs)
        task.completed = True
        print(f"  -> [Core] Task {task.id} FINISHED calculation.")
        return task.result

# --- SIMULATION CONFIGURATION ---
if __name__ == "__main__":
    engine = OutOfOrderEngine()

    # Define the tasks exactly from our example
    # We add an artificial sleep to A to simulate a slow dependency bottleneck
    def slow_add(): 
        time.sleep(0.3)
        return 5 + 5

    engine.add_task(Task(id='A', priority=1, dependencies=[],       operation=slow_add))
    engine.add_task(Task(id='B', priority=2, dependencies=[],       operation=lambda: 10 * 2))
    engine.add_task(Task(id='C', priority=3, dependencies=['A', 'B'], operation=lambda a, b: a + b)) # Stalled by A
    engine.add_task(Task(id='E', priority=4, dependencies=[],       operation=lambda: 50 - 10))   # Independent!
    engine.add_task(Task(id='F', priority=5, dependencies=[],       operation=lambda: 8 * 8))     # Independent!

    engine.run_pipeline()
