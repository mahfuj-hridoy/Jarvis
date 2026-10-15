clear;
clc;
close all;

P_in=1;
wavelength=1550;
N_turns=5;

R=linspace(5,30,50);
R_critical=12;

loss=1.5*N_turns.*exp(-(R-R_critical)/5);
loss(R>25)=0.05;

rng(20);
noise=0.01*randn(size(R));

P_measured=P_in*10.^(-loss/10)+noise;
P_measured(P_measured<=0)=0.000001;

measured_loss=10*log10(P_in./P_measured);

N=[1 2 3 5 8 10];

R1=[8 12 15 20];

L1=1.5*exp(-(R1-R_critical)/5);

figure;

plot(R,loss,'b-','LineWidth',2);
hold on;
plot(R,measured_loss,'ro');

grid on;
xlabel('Bend Radius (mm)');
ylabel('Bending Loss (dB)');
title('Bending Loss vs Bend Radius');
legend('Theoretical','Measured');

figure;

plot(N,N*L1(1),'-or','LineWidth',2);
hold on;
plot(N,N*L1(2),'-oy','LineWidth',2);
plot(N,N*L1(3),'-og','LineWidth',2);
plot(N,N*L1(4),'-ob','LineWidth',2);

grid on;
xlabel('Number of Turns');
ylabel('Bending Loss (dB)');
title('Bending Loss vs Number of Turns');
legend('R=8 mm','R=12 mm','R=15 mm','R=20 mm');