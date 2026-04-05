(async () => {
  const db = await new Promise((resolve, reject) => {
    const req = indexedDB.open("hbaDB");
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = reject;
  });
  console.log("stores:", Array.from(db.objectStoreNames));
  const storeName = db.objectStoreNames[0];
  const tx = db.transaction(storeName, "readonly");
  const store = tx.objectStore(storeName);
  const req = store.getAll();
  req.onsuccess = async (e) => {
    console.log("data:", JSON.stringify(e.target.result));
  };
})();
