export function NotImplemented({ feature }: { feature: string }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-20">
      <div className="h-16 w-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4 text-slate-400">
        <span>🚧</span>
      </div>
      <h3 className="text-xl font-bold text-slate-900 dark:text-white">{feature}</h3>
      <p className="text-slate-500 dark:text-slate-400 mt-2 max-w-xs">
        This subsystem is scheduled for a later build phase. Real implementation coming next — no mocks, no fake buttons.
      </p>
    </div>
  );
}
