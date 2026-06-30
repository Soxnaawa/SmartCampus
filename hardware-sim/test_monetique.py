import simulateur_terminal as st
from simulateur_terminal import charger_cartes, simuler_controle, simuler_debit, simuler_credit, se_connecter

if __name__ == "__main__":
    cartes = charger_cartes()
    carte = cartes[0]

    print("=" * 50)
    print(" CONNEXION CAISSIER")
    print("=" * 50)
    token = se_connecter("caissier", "caissier1234")
    if token:
        st.JWT_CAISSIER = token
        print(f"Token recupere : {token[:30]}...")
    else:
        print("Impossible de continuer sans token.")
        exit(1)

    print("\n" + "=" * 50)
    print(" TEST 1 : CONTROLE (acces / scolarite)")
    print("=" * 50)
    simuler_controle(carte)

    print("\n" + "=" * 50)
    print(" TEST 2 : DEBIT (paiement)")
    print("=" * 50)
    simuler_debit(carte, montant=800)

    print("\n" + "=" * 50)
    print(" TEST 3 : CREDIT (recharge)")
    print("=" * 50)
    simuler_credit(carte, montant=5000)