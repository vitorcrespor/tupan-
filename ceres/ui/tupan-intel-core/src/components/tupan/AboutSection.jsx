import React from 'react';
import { Image } from '@/components/ui/image';
import { Compass } from 'lucide-react';

const BG_URL = 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80';

export default function AboutSection() {
  return (
    <section className="relative w-full min-h-[480px] flex items-center justify-center overflow-hidden bg-background py-[142px] px-6">
      {/* Full-bleed background with slow float */}
      <div className="absolute inset-0 ab9-float origin-center">
        <Image
          src={BG_URL}
          alt=""
          fittingType="fill"
          className="w-full h-full pointer-events-none"
        />
        {/* Soft aqua wash to keep it on-brand over the photo */}
        <div className="absolute inset-0 bg-gradient-to-b from-aqua/10 via-transparent to-lagoon/15 mix-blend-soft-light" />
      </div>

      {/* Frosted glass card — reuses the app's aero-glass token */}
      <div className="ab9-drop relative z-10 w-[min(345px,100%)] p-5 flex flex-col gap-[62px] aero-glass rounded-[19px]">
        {/* Staggered entrance for inner content */}
        <div className="ab9-drop" style={{ animationDelay: '0.4s' }}>
          <div className="w-[45px] h-[45px] rounded-full bg-aqua/70 flex items-center justify-center shadow-aero">
            <Compass className="w-6 h-6 text-[hsl(186_70%_22%)]" strokeWidth={1.6} />
          </div>
        </div>

        <h2
          className="ab9-drop font-heading font-medium text-[40px] leading-[1.2] tracking-[-0.04em] text-[hsl(186_70%_22%)] m-0 max-w-[171px]"
          style={{ animationDelay: '0.65s' }}
        >
          Mission &amp; Vision
        </h2>

        <p
          className="ab9-drop font-body font-normal text-base leading-[1.3] tracking-[-0.01em] text-[hsl(186_70%_22%)] m-0"
          style={{ animationDelay: '0.9s' }}
        >
          Ceres turns raw market data into clear, predictive intelligence for
          real-estate professionals. We bridge measured data, valuation models,
          and AI insight so brokers and agencies can price, position, and act
          with confidence.
        </p>
      </div>
    </section>
  );
}
