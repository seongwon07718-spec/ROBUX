const db = await new Promise((resolve, reject) => {
    const req = indexedDB.open("hbaStore");
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = reject;
});
const tx = db.transaction("hbaObjectStore", "readonly");
const store = tx.objectStore("hbaObjectStore");
const req = store.get("hba_keys");
req.onsuccess = e => console.log(JSON.stringify(e.target.result));
