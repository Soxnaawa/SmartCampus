import { useState } from "react";

export default function Scan() {
  const [uid, setUid] = useState("SC-2025-00001");
  const [montant, setMontant] = useState(500);

  const handleClick = () => {
    alert(
      "Ce bouton necessite un payload signe (nonce + signature RSA) genere par le module hardware de P2.\n\n" +
        "Pour un vrai test, lancer test_monetique.py depuis le dossier hardware-sim."
    );
  };

  return (
    <div>
      <h2>Simuler un scan</h2>
      <p className="muted" style={{ marginBottom: 20 }}>
        Le payload signe (nonce + signature RSA) est genere par le module
        hardware (P2) en Python. Cette page illustre le flux mais ne genere
        pas de vraie signature.
      </p>

      <div className="scan-card">
        <input
          type="text"
          value={uid}
          onChange={(e) => setUid(e.target.value)}
          placeholder="SC-2025-00001"
        />
        <input
          type="number"
          value={montant}
          onChange={(e) => setMontant(e.target.value)}
          placeholder="Montant en FCFA"
        />
        <button className="btn-coral" onClick={handleClick}>
          Envoyer le debit
        </button>
      </div>
    </div>
  );
}
