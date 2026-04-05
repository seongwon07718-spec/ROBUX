(async () => {
  const db = await new Promise((resolve, reject) => {
    const req = indexedDB.open("hbaStore");
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = reject;
  });
  const tx = db.transaction("hbaObjectStore", "readonly");
  const store = tx.objectStore("hbaObjectStore");
  const req = store.get("hba_keys");
  req.onsuccess = async (e) => {
    const keys = e.target.result;
    const exported = await crypto.subtle.exportKey("pkcs8", keys.privateKey);
    const b64 = btoa(String.fromCharCode(...new Uint8Array(exported)));
    console.log("PRIVATE_KEY:" + b64);
  };
})();
