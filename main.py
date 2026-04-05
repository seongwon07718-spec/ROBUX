(async () => {
  const db = await new Promise((resolve, reject) => {
    const req = indexedDB.open("hbaDB");
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = reject;
  });
  const tx = db.transaction("hbaObjectStore", "readonly");
  const store = tx.objectStore("hbaObjectStore");
  const req = store.getAll();
  req.onsuccess = async (e) => {
    const keys = e.target.result[0];
    const exported = await crypto.subtle.exportKey("pkcs8", keys.privateKey);
    const b64 = btoa(String.fromCharCode(...new Uint8Array(exported)));
    console.log("PRIVATE_KEY=" + b64);
  };
})();
