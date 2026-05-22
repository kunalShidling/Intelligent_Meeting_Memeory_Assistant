export default function InlineRegistrationCard({ face, name, onNameChange, onRegister, isSaving }) {
  const imageSrc = face?.preview;
  const canSubmit = Boolean(name && name.trim()) && Boolean(imageSrc) && !isSaving;

  return (
    <div className="flex flex-wrap items-center gap-3 bg-white/90 border border-amber-100 rounded-2xl p-3 shadow-sm transition">
      <div className="w-14 h-14 rounded-full overflow-hidden border border-amber-100 bg-amber-50/60 flex items-center justify-center text-xs text-slate-500">
        {imageSrc ? (
          <img src={imageSrc} alt="Unknown face" className="w-full h-full object-cover" />
        ) : (
          <span>No image</span>
        )}
      </div>
      <div className="flex-1 min-w-[180px] space-y-2">
        <div className="text-xs uppercase tracking-wide text-slate-500">Unregistered face</div>
        <input
          type="text"
          placeholder="Enter name"
          className="w-full rounded-xl border border-amber-100 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
        />
      </div>
      <button
        onClick={onRegister}
        disabled={!canSubmit}
        className={`px-3 py-2 rounded-xl text-sm font-semibold transition ${canSubmit
          ? 'bg-teal-600 text-white hover:bg-teal-700'
          : 'bg-slate-100 text-slate-400 cursor-not-allowed'}`}
      >
        {isSaving ? 'Saving...' : 'Save'}
      </button>
    </div>
  );
}
